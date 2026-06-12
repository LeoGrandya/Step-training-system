// 深色主题 tooltip 公共配置
export function tt(trigger: 'axis' | 'item' = 'axis') {
  return {
    trigger,
    backgroundColor: '#ffffff',
    borderColor: '#cbd5e1',
    borderWidth: 1,
    textStyle: { color: '#1e293b', fontSize: 10 },
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 6px;'
  } as const;
}
