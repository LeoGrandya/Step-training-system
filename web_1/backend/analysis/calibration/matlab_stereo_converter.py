"""Convert MATLAB stereo calibration JSON into runtime stereo_params format."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StereoConvertError(ValueError):
    """Raised when input JSON cannot be converted to stereo params."""


@dataclass(frozen=True)
class StereoParams:
    k1: list[list[float]]
    dist1: list[list[float]]
    k2: list[list[float]]
    dist2: list[list[float]]
    r: list[list[float]]
    t: list[list[float]]
    image_size: list[int] | None

    def to_runtime_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "K1": self.k1,
            "dist1": self.dist1,
            "K2": self.k2,
            "dist2": self.dist2,
            "R": self.r,
            "T": self.t,
            "unit": "meter",
            "calibration_notes": {
                "source": "converted_from_matlab_json",
            },
        }
        if self.image_size is not None:
            out["image_size"] = self.image_size
            out["image_width"] = int(self.image_size[0])
            out["image_height"] = int(self.image_size[1])
        return out


def _coerce_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise StereoConvertError(f"{field} 包含非数值项: {value!r}") from exc


def _matrix(
    data: Any,
    *,
    rows: int | None,
    cols: int | None,
    field: str,
) -> list[list[float]]:
    if not isinstance(data, list) or not data:
        raise StereoConvertError(f"{field} 必须是二维数组")
    matrix: list[list[float]] = []
    for r_idx, row in enumerate(data):
        if not isinstance(row, list):
            raise StereoConvertError(f"{field}[{r_idx}] 必须是数组")
        matrix.append([_coerce_float(v, field) for v in row])
    if rows is not None and len(matrix) != rows:
        raise StereoConvertError(f"{field} 行数应为 {rows}，当前 {len(matrix)}")
    if cols is not None:
        for row in matrix:
            if len(row) != cols:
                raise StereoConvertError(f"{field} 列数应为 {cols}")
    return matrix


def _vector_as_col(data: Any, *, field: str) -> list[list[float]]:
    if not isinstance(data, list) or not data:
        raise StereoConvertError(f"{field} 必须是数组")
    # Accept [x,y,z], [[x],[y],[z]], [[x,y,z]]
    if all(not isinstance(v, list) for v in data):
        vec = [_coerce_float(v, field) for v in data]
    elif len(data) == 1 and isinstance(data[0], list):
        vec = [_coerce_float(v, field) for v in data[0]]
    else:
        try:
            vec = [_coerce_float(v[0], field) for v in data]  # type: ignore[index]
        except Exception as exc:  # noqa: BLE001
            raise StereoConvertError(f"{field} 格式错误") from exc
    if len(vec) != 3:
        raise StereoConvertError(f"{field} 长度应为 3，当前 {len(vec)}")
    return [[vec[0]], [vec[1]], [vec[2]]]


def _pick(raw: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in raw:
            return raw[key]
    return None


def _extract_image_size(raw: dict[str, Any]) -> list[int] | None:
    size = _pick(raw, ["image_size", "ImageSize", "imageSize"])
    if isinstance(size, list) and len(size) >= 2:
        return [int(size[0]), int(size[1])]
    w = _pick(raw, ["image_width", "imageWidth", "width"])
    h = _pick(raw, ["image_height", "imageHeight", "height"])
    if w is not None and h is not None:
        return [int(w), int(h)]
    return None


def _is_matlab_intrinsic(matrix_3x3: list[list[float]]) -> bool:
    """MATLAB stores principal point in last row for IntrinsicMatrix."""
    return (
        abs(matrix_3x3[0][2]) < 1e-9
        and abs(matrix_3x3[1][2]) < 1e-9
        and abs(matrix_3x3[2][2] - 1.0) < 1e-6
        and (abs(matrix_3x3[2][0]) > 1e-6 or abs(matrix_3x3[2][1]) > 1e-6)
    )


def _transpose_3x3(m: list[list[float]]) -> list[list[float]]:
    return [[m[r][c] for r in range(3)] for c in range(3)]


def _dist_from_camera_block(block: dict[str, Any], *, field: str) -> list[list[float]]:
    radial = block.get("RadialDistortion")
    tangential = block.get("TangentialDistortion")
    if not isinstance(radial, list):
        return [[0.0, 0.0, 0.0, 0.0, 0.0]]
    k1 = _coerce_float(radial[0], field) if len(radial) >= 1 else 0.0
    k2 = _coerce_float(radial[1], field) if len(radial) >= 2 else 0.0
    k3 = _coerce_float(radial[2], field) if len(radial) >= 3 else 0.0
    p1 = 0.0
    p2 = 0.0
    if isinstance(tangential, list):
        p1 = _coerce_float(tangential[0], field) if len(tangential) >= 1 else 0.0
        p2 = _coerce_float(tangential[1], field) if len(tangential) >= 2 else 0.0
    return [[k1, k2, p1, p2, k3]]


def _extract_matlab_nested(raw: dict[str, Any]) -> tuple[Any, Any, Any, Any] | None:
    c1 = raw.get("Camera1")
    c2 = raw.get("Camera2")
    r = raw.get("RotationOfCamera2")
    t = raw.get("TranslationOfCamera2")
    if not isinstance(c1, dict) or not isinstance(c2, dict) or r is None or t is None:
        return None
    return (
        c1.get("IntrinsicMatrix"),
        c2.get("IntrinsicMatrix"),
        r,
        t,
    )


def convert_matlab_stereo_json(input_obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(input_obj, dict):
        raise StereoConvertError("输入 JSON 顶层必须是对象")

    # Passthrough if already in runtime format
    if all(k in input_obj for k in ("K1", "K2", "R", "T")):
        return input_obj

    k1 = _pick(input_obj, ["K1", "cameraMatrix1", "CameraMatrix1", "IntrinsicMatrix1"])
    k2 = _pick(input_obj, ["K2", "cameraMatrix2", "CameraMatrix2", "IntrinsicMatrix2"])
    d1 = _pick(input_obj, ["dist1", "distCoeffs1", "DistortionCoefficients1", "radialTangential1"])
    d2 = _pick(input_obj, ["dist2", "distCoeffs2", "DistortionCoefficients2", "radialTangential2"])
    r = _pick(input_obj, ["R", "rotationMatrix", "RotationOfCamera2"])
    t = _pick(input_obj, ["T", "translationVector", "TranslationOfCamera2"])

    nested = _extract_matlab_nested(input_obj)
    if nested is not None and (k1 is None or k2 is None):
        k1, k2, r, t = nested
        d1 = _dist_from_camera_block(input_obj["Camera1"], field="Camera1")
        d2 = _dist_from_camera_block(input_obj["Camera2"], field="Camera2")

    if k1 is None or k2 is None or r is None or t is None:
        raise StereoConvertError("缺少关键字段，至少需要 K1/K2/R/T（或其 MATLAB 等效字段）")

    # Distortion can be missing in some exports; default to zero.
    if d1 is None:
        d1 = [[0.0, 0.0, 0.0, 0.0, 0.0]]
    if d2 is None:
        d2 = [[0.0, 0.0, 0.0, 0.0, 0.0]]

    k1_m = _matrix(k1, rows=3, cols=3, field="K1")
    k2_m = _matrix(k2, rows=3, cols=3, field="K2")
    if _is_matlab_intrinsic(k1_m):
        k1_m = _transpose_3x3(k1_m)
    if _is_matlab_intrinsic(k2_m):
        k2_m = _transpose_3x3(k2_m)
    image_size = _extract_image_size(input_obj)
    # MATLAB ImageSize is [height, width], runtime expects [width, height].
    if "Camera1" in input_obj and isinstance(input_obj["Camera1"], dict):
        raw_size = input_obj["Camera1"].get("ImageSize")
        if isinstance(raw_size, list) and len(raw_size) >= 2:
            image_size = [int(raw_size[1]), int(raw_size[0])]

    t_m = _vector_as_col(t, field="T")
    world_units = str(input_obj.get("WorldUnits", "")).lower().strip()
    if world_units.startswith("milli"):
        t_m = [[v[0] / 1000.0] for v in t_m]

    params = StereoParams(
        k1=k1_m,
        dist1=_matrix(d1, rows=1, cols=5, field="dist1"),
        k2=k2_m,
        dist2=_matrix(d2, rows=1, cols=5, field="dist2"),
        r=_matrix(r, rows=3, cols=3, field="R"),
        t=t_m,
        image_size=image_size,
    )
    return params.to_runtime_dict()


def convert_matlab_stereo_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StereoConvertError(f"标定 JSON 解析失败: {exc}") from exc
    converted = convert_matlab_stereo_json(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8")
    return converted
