#!/usr/bin/env bash

set -euo pipefail


echo "=== Novelcast installer ==="


OS="$(uname -s)"
ARCH="$(uname -m)"


echo "Detected:"
echo " OS: $OS"
echo " ARCH: $ARCH"


install_linux_packages()
{
    if command -v apt >/dev/null; then

        sudo apt update

        sudo apt install -y \
            curl \
            git \
            python3 \
            python3-pip \
            python3-venv \
            build-essential

    fi
}


install_node()
{
    if command -v node >/dev/null; then

        NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)

        if [ "$NODE_VERSION" -ge 18 ]; then
            echo "Node OK"
            return
        fi

    fi


    echo "Installing Node.js"


    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -

    sudo apt install -y nodejs
}


install_uv()
{
    if command -v uv >/dev/null; then
        echo "uv OK"
        return
    fi


    echo "Installing uv"

    curl -LsSf https://astral.sh/uv/install.sh | sh


    export PATH="$HOME/.local/bin:$PATH"


    if ! command -v uv >/dev/null; then
        echo "uv installation failed"
        exit 1
    fi
}



case "$OS" in

Linux*)
    install_linux_packages
    ;;

Darwin*)
    echo "macOS detected"

    if ! command -v brew >/dev/null; then
        echo "Homebrew required"
        echo "Install from https://brew.sh"
        exit 1
    fi

    brew install python node curl

    ;;

*)
    echo "Unsupported OS: $OS"
    exit 1

esac



install_node
install_uv



echo "Installing Python dependencies"

uv sync



echo "Installing frontend dependencies"

npm install

echo "Installing Prettier"

npm install --save-dev prettier



echo ""
echo "================================"
echo " Installation complete"
echo " Run:"
echo ""
echo "   make dev"
echo ""
echo "================================"