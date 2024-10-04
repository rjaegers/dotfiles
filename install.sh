#!/bin/bash

# Install Starship (https://starship.rs) shell
sh -c "$(wget -qO- https://starship.rs/install.sh)" -y -f > /dev/null
grep -qxF 'eval "$(starship init bash)"' ~/.bashrc || echo 'eval "$(starship init bash)"' >> ~/.bashrc
ln -sf "$(pwd)/dotfiles/.config/starship.toml" ~/.config/starship.toml

# Install eza (https://eza.rocks) a modern alternative to ls
wget -qO- https://github.com/eza-community/eza/releases/latest/download/eza_$(uname -m)-unknown-linux-gnu.tar.gz | tar -xzv -C /usr/local/bin

git clone https://github.com/eza-community/eza-themes.git > /dev/null
mkdir -p ~/.config/eza
ln -sf "$(pwd)/eza-themes/themes/gruvbox-dark.yml" ~/.config/eza/theme.yml
