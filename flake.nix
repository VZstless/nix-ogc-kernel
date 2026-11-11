{
  description = "OpenGamingCollective Linux Kernel for NixOS";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-compat = {
      url = "github:NixOS/flake-compat";
      flake = false;
    };
  };
  outputs = inputs@{ self, nixpkgs, flake-parts, ... }:

    let
      lib = inputs.nixpkgs.lib;
      pkgs = import inputs.nixpkgs {
        inherit system;
      };
      kernels = lib.filterAttrs (_: lib.isDerivation) (pkgs.callPackage ./kernel { });
      system = "x86_64-linux";

      mkApp = name: script: {
        type = "app";
        program = lib.getExe (pkgs.writeShellApplication {
          inherit name;
          runtimeInputs = [
            (pkgs.python3.withPackages (ps: [ ps.requests ]))
            pkgs.cacert
            pkgs.git
            pkgs.nix
          ];
          text = ''
            exec python3 ${script} "$@"
          '';
        });
      };
    in
    {
      packages.${system} = kernels // {
        default = kernels.linux-ogc;
      };

      apps.${system} = {
        update = mkApp "update" ./update.py;
        default = self.apps.${system}.update;
      };
    };
}
