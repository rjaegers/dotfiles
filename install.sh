#!/bin/bash

# Install Starship (https://starship.rs) shell
wget -qO- https://starship.rs/install.sh | sh
echo 'eval "$(starship init bash)' >> ~/.bashrc
