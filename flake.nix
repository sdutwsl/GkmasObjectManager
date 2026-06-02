{
  description = "Development shell for GkmasObjectManager";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      inherit (pkgs) lib;

      python = pkgs.python312;
      pythonPackages = python.pkgs;

      wheelBuildInputs = lib.optionals pkgs.stdenv.hostPlatform.isLinux [
        pkgs.stdenv.cc.cc.lib
      ];

      wheelNativeBuildInputs = lib.optionals pkgs.stdenv.hostPlatform.isLinux [
        pkgs.autoPatchelfHook
      ];

      texture2ddecoder = pythonPackages.buildPythonPackage rec {
        pname = "texture2ddecoder";
        version = "1.0.6";
        format = "wheel";

        src = pkgs.fetchPypi {
          inherit pname version format;
          dist = "cp311";
          python = "cp311";
          abi = "abi3";
          platform = "manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64";
          hash = "sha256-CbmOpNZuIaykJVhyfcYJqKlS4rbrCdDujg5SuhS3hIo=";
        };

        nativeBuildInputs = wheelNativeBuildInputs;
        buildInputs = wheelBuildInputs;
        pythonImportsCheck = [ "texture2ddecoder" ];
      };

      etcpak = pythonPackages.buildPythonPackage rec {
        pname = "etcpak";
        version = "0.9.15";
        format = "wheel";

        src = pkgs.fetchPypi {
          inherit pname version format;
          dist = "cp37";
          python = "cp37";
          abi = "abi3";
          platform = "manylinux_2_17_x86_64.manylinux2014_x86_64";
          hash = "sha256-t1JIxIacf93x5bukvgKlBNoIz/sXQ03NtbxhiGnU6go=";
        };

        nativeBuildInputs = wheelNativeBuildInputs;
        buildInputs = wheelBuildInputs;
        propagatedBuildInputs = [ pythonPackages.archspec ];
        pythonImportsCheck = [ "etcpak" ];
      };

      pyfmodex = pythonPackages.buildPythonPackage rec {
        pname = "pyfmodex";
        version = "0.7.2";
        format = "wheel";

        src = pkgs.fetchPypi {
          inherit pname version format;
          dist = "py3";
          python = "py3";
          abi = "none";
          platform = "any";
          hash = "sha256-HEIRK3iOgO57S1euJbu8CpjrHjKo58nhJGaYzfcu+p0=";
        };
      };

      unitypy = pythonPackages.buildPythonPackage rec {
        pname = "UnityPy";
        version = "1.10.18";
        format = "wheel";

        src = pkgs.fetchPypi {
          inherit pname version format;
          dist = "cp312";
          python = "cp312";
          abi = "cp312";
          platform = "manylinux_2_17_x86_64";
          hash = "sha256-NUSzlMDRGwzgwgowY4tYTCWEGV8tZIlPy72pCF6B55Y=";
        };

        nativeBuildInputs =
          wheelNativeBuildInputs
          ++ lib.optionals pkgs.stdenv.hostPlatform.isLinux [
            pkgs.prelink
          ];
        buildInputs = wheelBuildInputs;
        propagatedBuildInputs = [
          pythonPackages.brotli
          pythonPackages.fsspec
          pythonPackages.lz4
          pythonPackages.pillow
          pythonPackages.tabulate
          etcpak
          pyfmodex
          texture2ddecoder
        ];

        postFixup = lib.optionalString pkgs.stdenv.hostPlatform.isLinux ''
          execstack -c "$out/${python.sitePackages}/UnityPy/lib/FMOD/Linux/x86_64/libfmod.so"
        '';

        pythonImportsCheck = [ "UnityPy" ];
      };

      pythonEnv = python.withPackages (
        ps: [
          ps.cryptography
          ps.flask
          ps.pandas
          ps.pillow
          ps.protobuf
          ps.pydub
          ps.pyyaml
          ps.requests
          ps.rich
          ps.tqdm
          unitypy
        ]
      );
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pythonEnv
          pkgs.ffmpeg
          pkgs.git
        ];

        shellHook = ''
          export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"
          export LD_LIBRARY_PATH="${lib.makeLibraryPath wheelBuildInputs}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        '';
      };
    };
}
