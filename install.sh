#!/bin/bash

# Install Starship (https://starship.rs) shell
sh -c "$(wget -qO- https://starship.rs/install.sh)" -y -f > /dev/null
grep -qxF 'eval "$(starship init bash)"' ~/.bashrc || echo 'eval "$(starship init bash)"' >> ~/.bashrc
