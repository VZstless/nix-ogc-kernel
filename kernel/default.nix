{
  callPackage,
  ...
}@args:
let
  variants = import ./variants.nix;
  mkOgcKernel = callPackage ./mkOgcKernel.nix args;
in
  builtins.mapAttrs
    (pname: spec: mkOgcKernel (spec // { inherit pname; }))
    variants
