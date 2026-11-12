{
  description = "OpenGamingCollective Linux Kernel for NixOS";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-compat = {
      url = "github:NixOS/flake-compat";
      flake = false;
    };

    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
  outputs =
    inputs@{
      self,
      nixpkgs,
      flake-parts,
      ...
    }:

    let
      lib = inputs.nixpkgs.lib;
      pkgs = import inputs.nixpkgs {
        inherit system;
      };
      kernels = lib.filterAttrs (_: lib.isDerivation) (pkgs.callPackage ./kernel { });
      system = "x86_64-linux";
      treefmtEval = inputs.treefmt-nix.lib.evalModule pkgs ./treefmt.nix;

      mkPythonApp = name: script: {
        type = "app";
        program = lib.getExe (
          pkgs.writeShellApplication {
            inherit name;
            runtimeInputs = [
              (pkgs.python3.withPackages (ps: [ ps.requests ]))
              pkgs.cacert
              pkgs.git
            ];
            text = ''
              exec python3 ${script} "$@"
            '';
          }
        );
      };

      mkBashApp = name: text: {
        type = "app";
        program = lib.getExe (
          pkgs.writeShellApplication {
            inherit name text;
            runtimeInputs = [
              pkgs.actionlint
              pkgs.shellcheck
              pkgs.python3Packages.pyflakes
            ];
          }
        );
      };
    in
    {
      packages.${system} = kernels // {
        default = kernels.linux-ogc;
      };

      formatter.${system} = treefmtEval.config.build.wrapper;

      checks.${system}.formatting = treefmtEval.config.build.check self;

      apps.${system} = {
        update = mkPythonApp "update" ./update.py;
        lint = mkBashApp "lint" ''
          actionlint
          nix fmt
          pyflakes ./update.py
        '';
        default = self.apps.${system}.update;
      };
    };
}
