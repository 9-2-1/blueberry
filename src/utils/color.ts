// RGB 到 OKLCH 的转换函数
// 简化实现，实际项目中可以使用更精确的转换库
export function rgbToOklch(r: number, g: number, b: number) {
	// 将 RGB 转换为线性 RGB
	const rLinear = r / 255 < 0.04045 ? r / 255 / 12.92 : Math.pow((r / 255 + 0.055) / 1.055, 2.4);
	const gLinear = g / 255 < 0.04045 ? g / 255 / 12.92 : Math.pow((g / 255 + 0.055) / 1.055, 2.4);
	const bLinear = b / 255 < 0.04045 ? b / 255 / 12.92 : Math.pow((b / 255 + 0.055) / 1.055, 2.4);

	// 转换为 XYZ 颜色空间
	const x = rLinear * 0.4124564 + gLinear * 0.3575761 + bLinear * 0.1804375;
	const y = rLinear * 0.2126729 + gLinear * 0.7151522 + bLinear * 0.0721750;
	const z = rLinear * 0.0193339 + gLinear * 0.1191920 + bLinear * 0.9503041;

	// 转换为 L*a*b* 颜色空间
	const xn = 0.95047;
	const yn = 1.0;
	const zn = 1.08883;

	const fx = x / xn > 0.008856 ? Math.pow(x / xn, 1/3) : 7.787 * (x / xn) + 16/116;
	const fy = y / yn > 0.008856 ? Math.pow(y / yn, 1/3) : 7.787 * (y / yn) + 16/116;
	const fz = z / zn > 0.008856 ? Math.pow(z / zn, 1/3) : 7.787 * (z / zn) + 16/116;

	const l = 116 * fy - 16;
	const a = 500 * (fx - fy);
	const lab_b = 200 * (fy - fz);

	// 转换为 OKLCH 颜色空间（简化实现）
	const c = Math.sqrt(a * a + lab_b * lab_b);
	let h = Math.atan2(lab_b, a) * 180 / Math.PI;
	if (h < 0) h += 360;

	return { l: l / 100, c: c / 100, h };
}

// 从颜色字符串中提取 RGB 值
export function parseColor(color: string): { r: number; g: number; b: number } | null {
	// 处理 #RRGGBB 格式
	const hexMatch = color.match(/^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
	if (hexMatch) {
		return {
			r: parseInt(hexMatch[1], 16),
			g: parseInt(hexMatch[2], 16),
			b: parseInt(hexMatch[3], 16)
		};
	}

	// 处理 rgb(r, g, b) 格式
	const rgbMatch = color.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
	if (rgbMatch) {
		return {
			r: parseInt(rgbMatch[1], 10),
			g: parseInt(rgbMatch[2], 10),
			b: parseInt(rgbMatch[3], 10)
		};
	}

	// 处理 rgba(r, g, b, a) 格式
	const rgbaMatch = color.match(/^rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)$/);
	if (rgbaMatch) {
		return {
			r: parseInt(rgbaMatch[1], 10),
			g: parseInt(rgbaMatch[2], 10),
			b: parseInt(rgbaMatch[3], 10)
		};
	}

	// 默认颜色
	return null;
}

// 获取主题色相关的颜色值
export function getThemeColors(color: string) {
	const rgb = parseColor(color) || { r: 0, g: 0, b: 0 };
	const oklch = rgbToOklch(rgb.r, rgb.g, rgb.b);

	return {
		文本颜色: `oklch(${oklch.l * 0.6}, ${oklch.c}, ${oklch.h})`,
		背景颜色: `oklch(${oklch.l * 0.9}, ${oklch.c * 0.5}, ${oklch.h})`,
		强调字体颜色: `oklch(${oklch.l * 0.8}, ${oklch.c * 0.5}, ${oklch.h})`
	};
}