# Nix packages for OpenGamingCollective Linux Kernel

WARNING: this repo is under actively construction so the internal and build result may have breaking change in near future.

## Building

flake building target:
```shell
nix build .#linux-ogc
nix build .#linux-ogc-lts
```

traditional nix-way building target:
```shell
nix-build -A packages.x86_64-linux.linux-ogc
nix-build -A packages.x86_64-linux.linux-ogc-lts
```

## Integrate into your machine

(TODO)
