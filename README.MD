# URMconfig - Remote Work Readiness Diagnostic System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-green.svg)
![License](https://img.shields.io/badge/License-Custom-red.svg)

**Comprehensive system diagnostics tool for remote work capability assessment**

[🚀 Quick Start](#-quick-start) • [🔧 Installation](#-installation)

</div>

## 📋 Overview

URMconfig is a professional desktop application designed to comprehensively assess computer systems for remote work readiness. The application automatically evaluates all critical system components and provides detailed reports on workplace compatibility with remote work requirements.

### ✨ Key Features

- 🌐 **Internet Speed Testing** - Download/upload speeds and latency measurement
- 💻 **Hardware Analysis** - CPU, RAM, and GPU compatibility checks
- 🔌 **Network Equipment Validation** - Ethernet adapter detection and specifications
- 🖥️ **Display Diagnostics** - Screen resolution and graphics compatibility
- 💾 **Storage Analysis** - Available disk space verification
- 🎤 **Peripheral Testing** - Microphone and webcam functionality
- 🔧 **Citrix Compatibility** - Virtualization platform support verification
- 📊 **Comprehensive Reporting** - Exportable results with detailed recommendations

## 🎯 System Requirements

### Minimum Requirements for Testing:
- **Internet Speed**: ≥ 75 Mbps
- **Network**: Ethernet connectivity capability
- **CPU**: ≥ 2 cores
- **RAM**: ≥ 4 GB
- **Display**: ≥ 1600×900 resolution
- **Storage**: ≥ 10 GB free space
- **Peripherals**: Microphone and HD webcam

### Software Dependencies:
- Python 3.7+
- PyQt5
- OpenCV (cv2)
- PyAudio
- psutil
- WMI (Windows)

## 🚀 Quick Start

### Option 1: Pre-built Executable
1. Download the latest release from the releases page
2. Run `URMconfig.exe` (Windows) or the appropriate executable for your platform
3. Click "Start Test" to begin diagnostics

### Option 2: Run from Source
```bash
# Clone the repository
git clone https://github.com/nedomru/URMconfig
cd urmconfig

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## 🔧 Installation

### Prerequisites
Ensure you have Python 3.7 or higher installed on your system.

### Install Dependencies
```bash
pip install PyQt5 psutil opencv-python-headless pyaudio wmi
```

### Building Executable
To create a standalone executable:
```bash
# Install PyInstaller
pip install pyinstaller

# Build using the provided spec file
pyinstaller URMconfig.spec
```

The executable will be created in the `dist/` directory.

## 📖 How It Works

### Diagnostic Process
The application performs diagnostics in four main phases:

1. **🌐 Network Testing**
   - Internet speed measurement using speedtest.net
   - Ethernet adapter detection and configuration
   - Network stability assessment

2. **💻 Hardware Validation**
   - CPU core count and specifications
   - RAM capacity and frequency
   - GPU detection and driver verification
   - Display resolution capabilities

3. **💾 Storage Analysis**
   - Available disk space on system drive
   - Performance characteristics

4. **🎤 Peripheral Detection**
   - Microphone availability and functionality
   - Webcam detection with resolution testing
   - Audio/video quality assessment

### Output and Reporting
- Real-time progress updates with animated status indicators
- Color-coded results (✅ Pass / ❌ Fail)
- Detailed technical specifications for each component
- Copy-to-clipboard functionality for easy sharing
- Comprehensive final report with recommendations

## 🏗️ Project Structure

```
urmconfig/
├── main.py                 # Main application entry point
├── URMconfig.spec         # PyInstaller configuration
├── README.md              # Project documentation
├── .gitignore            # Git ignore rules
├── assets/               # Application resources
│   ├── logo.png         # Application logo
│   └── app-logo.png     # Icon for executable
└── utils/               # Utility modules
    ├── __init__.py      # Package initialization
    ├── cpu.py          # CPU information utilities
    ├── gpu.py          # GPU detection and analysis
    ├── internet.py     # Network testing functions
    ├── peripherals.py  # Audio/video device detection
    └── system.py       # System information utilities
```

## 🔍 Technical Details

### Architecture
- **GUI Framework**: PyQt5 with custom styled components
- **Threading**: Background diagnostics to maintain UI responsiveness
- **Modular Design**: Separated utility modules for different system aspects

### Key Components

#### Main Application (`main.py`)
- `SystemDiagnosticsApp`: Main window and UI management
- `DiagnosticsThread`: Background worker for system testing
- `RoundedButton`: Custom UI component with modern styling

#### Utility Modules
- `utils.cpu`: CPU information retrieval and analysis
- `utils.gpu`: Graphics card detection and driver verification
- `utils.internet`: Network speed testing and adapter detection
- `utils.peripherals`: Audio/video device enumeration
- `utils.system`: OS compatibility and system information

### Citrix Compatibility Matrix
The application includes comprehensive Citrix Workspace App compatibility checking based on:
- Windows 10/11 build numbers
- Specific version requirements for each OS build
- Version recommendation engine

## 🛠️ Development

### Setting up Development Environment
```bash
# Clone and setup
git clone https://github.com/nedomru/URMconfig
cd urmconfig
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running Tests
```bash
python main.py
```

### Building for Distribution
```bash
pyinstaller URMconfig.spec
```

## 📊 Diagnostic Criteria

| Component | Requirement | Test Method |
|-----------|-------------|-------------|
| Internet Speed | ≥75 Mbps download | speedtest-cli |
| CPU Cores | ≥2 physical cores | psutil + registry |
| RAM | ≥4 GB total | psutil memory info |
| Display | ≥1600×900 resolution | PyQt5 desktop geometry |
| Storage | ≥10 GB free space | psutil disk usage |
| Ethernet | Active adapter present | netsh/ip commands |
| Microphone | Functional device | PyAudio enumeration |
| Webcam | HD capability (≥720p) | OpenCV device testing |
| Citrix | OS build compatibility | Version matrix lookup |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project uses a custom license. Please refer to the [license agreement](https://sos.dom.ru/services/license_URM.pdf) for terms and conditions.

## 🆘 Support

For support and questions:
- Check the documentation above
- Review the license agreement
- Contact system administrators for enterprise deployments

## 🏆 Acknowledgments

- Built with PyQt5 for cross-platform GUI development
- Uses OpenCV for advanced camera detection
- Powered by speedtest-cli for accurate network measurements
- System information provided by psutil

---

<div align="center">
<strong>URMconfig - Ensuring Remote Work Readiness</strong>
</div>
