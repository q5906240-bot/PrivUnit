# 本地脱敏客户端架构

## 运行链路

1. Tauri/React 负责文件选择、材料类型校验、预览、候选框复核和导出操作。
2. Python sidecar 负责本地分析与导出，命令入口为 `python -m redactor.cli`。
3. RapidOCR ONNX 模型随客户端放在 `resources/ocr/rapidocr`，sidecar 启动时优先从 Tauri resource 路径加载并校验。
4. 候选框统一使用归一化坐标，前端显示和后端导出使用同一份 JSON。

## 识别策略

- OCR：调用随客户端打包的 RapidOCR ONNX 模型；如果模型缺失，sidecar 直接报错，避免误以为已自动识别。
- 文本规则：本人姓名只匹配用户输入的姓名；身份证号、手机号使用正则；单位、地址、部门使用关键词。
- 视觉规则：OpenCV 检测红色公章、人脸/证件照和页眉区域的疑似 logo。

## 导出策略

- 图片：Pillow 直接对已确认区域做像素覆盖。
- 数字 PDF：PyMuPDF redaction annotation + `apply_redactions`，删除底层文本并覆盖图片像素。
- 扫描 PDF：可走栅格化导出，避免底图敏感像素残留。

## 打包注意

- 桌面端需要 Rust/Cargo。
- 使用 `./scripts/build_desktop.sh` 先打包 sidecar，再执行 Tauri build；脚本固定使用 macOS 可用的 `en_US.UTF-8` locale，避免 DMG 阶段 perl locale 崩溃。
- Windows 使用 `.\scripts\build_desktop.ps1`，会先生成 `redactor-sidecar-x86_64-pc-windows-msvc.exe`，再由 Tauri 生成安装包。
- Linux/国产桌面系统使用 `./scripts/build_desktop_linux.sh`，会生成 `.deb` 和 `.AppImage`。Ubuntu 桌面版、银河麒麟、统信 UOS 优先安装 `.deb`；依赖库不匹配时使用 `.AppImage` 兜底。
- Linux 运行依赖 WebKitGTK/GTK3/AppIndicator/librsvg。Debian/Ubuntu 系系统可安装 `libwebkit2gtk-4.1-0`、`libgtk-3-0`、`libayatana-appindicator3-1`、`librsvg2-2`；不同国产发行版包名可能略有差异。
- sidecar 可用 `python3 scripts/build_sidecar.py` 单独打包到 `src-tauri/binaries/`，文件名会按 Tauri externalBin 规则追加平台三元组。
- 当前资源内置 RapidOCR 三个 ONNX 模型和 OpenCV 人脸级联 XML；sidecar 二进制 smoke 已验证能离线输出身份证候选框。
- PyMuPDF 为 AGPL/商业双许可，闭源商业发布前需要处理授权或改为全栅格化方案。
