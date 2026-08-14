#!/usr/bin/env bash
set -e

# ANSI Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}      💾 LinuxDisk: 1-Line Installer for Ubuntu     ${NC}"
echo -e "${BLUE}====================================================${NC}"
echo ""

# Check root / sudo
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

echo -e "${YELLOW}📦 [1/4] Installing system dependencies (smartmontools, python3, python3-tk)...${NC}"
if command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq smartmontools python3 python3-tk python3-pip util-linux
elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y smartmontools python3 python3-tkinter util-linux
elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm smartmontools python tk util-linux
fi

INSTALL_DIR="/opt/linuxdisk"
echo -e "${YELLOW}📥 [2/4] Downloading latest LinuxDisk release from GitHub...${NC}"
$SUDO rm -rf "${INSTALL_DIR}"
$SUDO git clone --depth=1 https://github.com/alexuribarri/LinuxDisk.git "${INSTALL_DIR}"

echo -e "${YELLOW}🔗 [3/4] Creating system binary symlink at /usr/local/bin/linuxdisk...${NC}"
$SUDO chmod +x "${INSTALL_DIR}/linuxdisk"
$SUDO ln -sf "${INSTALL_DIR}/linuxdisk" /usr/local/bin/linuxdisk

echo -e "${YELLOW}🖥️  [4/4] Registering Ubuntu Desktop application launcher...${NC}"
$SUDO mkdir -p /usr/share/applications
$SUDO cp "${INSTALL_DIR}/assets/linuxdisk.desktop" /usr/share/applications/linuxdisk.desktop
$SUDO update-desktop-database /usr/share/applications >/dev/null 2>&1 || true

echo ""
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}  ✅ LinuxDisk has been successfully installed!     ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo ""
echo -e "🚀 To launch the Desktop GUI:  ${BLUE}linuxdisk${NC} (or search 'LinuxDisk' in Ubuntu App Grid)"
echo -e "📟 To launch in Terminal TUI: ${BLUE}linuxdisk --cli${NC}"
echo ""
