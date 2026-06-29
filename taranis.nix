{ self }:
{
  lib,
  config,
  pkgs,
  ...
}:

let
  cfg = config.services.taranis;
in
{
  options.services.taranis = {
    enable = lib.mkEnableOption "taranis";

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.system}.default;
      description = "Package for Taranis AI";
    };

    extraArgs = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Extra uvicorn args.";
      example = [
        "--reload"
      ];
    };

    host = lib.mkOption {
      type = lib.types.str;
      default = "0.0.0.0";
      description = "The host where Taranis AI should listen to.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8000;
      description = "The port Taranis AI should listen at.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.taranis = {
      description = "Taranis AI service";
      wantedBy = [ "multi-user.target" ];

      startLimitIntervalSec = 300;
      startLimitBurst = 30;

      serviceConfig = {
        ExecStart = "${lib.getExe' cfg.package "taranis-ai"} ${lib.escapeShellArgs cfg.extraArgs}";
        WorkingDirectory = "${self}"; # to load the yaml files
        DynamicUser = true;
        StateDirectoryMode = "0750";
        Restart = "on-failure";
        RestartSec = "10s";
      };
    };
  };
}
