/** ECharts tooltip 公共亮色主题配置。 */
export function tooltipTheme(trigger = 'axis') {
  return {
    trigger,
    backgroundColor: '#ffffff',
    borderColor: '#cbd5e1',
    borderWidth: 1,
    textStyle: { color: '#1e293b', fontSize: 10 },
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 6px;',
  };
}
