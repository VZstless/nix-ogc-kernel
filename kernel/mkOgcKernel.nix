{
  lib,
  fetchFromGitHub,
  buildLinux,
  ...
}:
lib.makeOverridable (
  {
    pname,
    version,
    modDirVersion,
    rev ? null,
    tag ? null,
    hash,
    owner ? "OpenGamingCollective",
    repo ? "linux",
    defconfig ? "defconfig",
    ...
  }@args:

  assert
    lib.xor (rev == null) (tag == null) || throw "mkOgcKernel: provide exactly one of `rev` or `tag`";

  buildLinux rec {
    inherit
      pname
      version
      modDirVersion
      defconfig
      ;
    src = fetchFromGitHub {
      inherit
        owner
        repo
        rev
        tag
        hash
        ;
    };
  }
)
