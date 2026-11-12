# Nix packages for OpenGamingCollective Linux Kernel

WARNING: this repo is under actively construction so the internal and build result may have breaking change in near future.

This repo is strongly inspired by [LanTian's nix-cachyos repo](https://github.com/xddxdd/nix-cachyos-kernel)

- `linux-ogc` follows the newest release of `OpenGamingCollective/linux`.
- `linux-ogc-lts` follows the latest commit of the `ogc-lts` branch.

According to OpenGamingCollective's document, this kernel is fully functional on asus devices, but I have no more asus devices so if you want to try this I won't stop you.

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

## Updating

`update.py` refreshes `flake.lock` and the kernel source pins in `kernel/versions.json`:

```shell
./update.py              # nix flake update + refresh both kernel pins
./update.py --check      # exit 1 when something is stale, write nothing
./update.py --no-flake-lock    # only refresh the kernel pins
./update.py --refresh-hashes   # re-download even if the ref did not move
```

## Integrate into your machine

If you are using flake, follow the master branch:
```nix
{
  inputs = {
    nix-ogc-kernel.url = "github:VZstless/nix-ogc-kernel/master";
  }
}
```
Currently this repo has no hydra CI available as I have no more devices to do this.

Then, in output:
```nix
{
  outputs = { self, nixpkgs, nix-ogc-kernel, ... }: {
    nixosConfigurations.<hostname> = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ({ pkgs, ... }: {
          nixpkgs.overlays = [
            (final: prev: {
              linux-ogc = nix-ogc-kernel.packages.${final.stdenv.hostPlatform.system}.linux-ogc;
              linux-ogc-lts = nix-ogc-kernel.packages.${final.stdenv.hostPlatform.system}.linux-ogc-lts;
            })
          ];

          boot.kernelPackages = pkgs.linuxPackagesFor pkgs.linux-ogc;
          # rest of your configuration
        })
      ];
    }
  }
}
```


