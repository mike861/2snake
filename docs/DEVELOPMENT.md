## 系统要求

- Python 3.6+
- Kivy 2.2.1+
- KivyMD 1.1.1+
- Pygame 2.5.0+

## 开发说明

要进行开发或修改，可以：

1. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

2. 安装开发依赖：
```bash
pip install -r config/requirements.txt
```

## 移动平台构建

使用 Buildozer 构建 Android 应用：

```bash
pip install buildozer
buildozer android debug
``` 