#!/bin/bash

# Install Starship (https://starship.rs) shell
sh -c "$(wget -qO- https://starship.rs/install.sh)" -y -f > /dev/null
grep -qxF 'eval "$(starship init bash)"' ~/.bashrc || echo 'eval "$(starship init bash)"' >> ~/.bashrc
ln -sf "$(pwd)/dotfiles/.config/starship.toml" ~/.config/starship.toml

# Install eza (https://eza.rocks) a modern alternative to ls
if [ "$(uname -m)" = "aarch64" ]; then
    # Work around https://github.com/eza-community/eza/issues/1060
    wget -qO- https://github.com/user-attachments/files/16258190/eza_aarch64-unknown-linux-gnu.tar.gz | tar -xzv -C /usr/local/bin
else
    wget -qO- https://github.com/eza-community/eza/releases/latest/download/eza_$(uname -m)-unknown-linux-gnu.tar.gz | tar -xzv -C /usr/local/bin
fi

git clone https://github.com/eza-community/eza-themes.git > /dev/null
mkdir -p ~/.config/eza
ln -sf "$(pwd)/eza-themes/themes/gruvbox-dark.yml" ~/.config/eza/theme.yml

ln -sf "$(pwd)/.bash-aliases" ~/.bash-aliases
