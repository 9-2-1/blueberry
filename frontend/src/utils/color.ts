import chroma from 'chroma-js';

// 获取主题色相关的颜色值
export function getThemeColors(color: string) {
  // 使用 chroma-js 来处理颜色转换
  const 颜色 = chroma(color);
  const [, c, h] = 颜色.oklch();

  return {
    文本颜色: chroma.oklch(0.5, c, h).css(),
    背景颜色: chroma.oklch(0.98, c * 0.1, h).css(),
    强调字体颜色: chroma.oklch(0.5, c, h).css(),
  };
}
