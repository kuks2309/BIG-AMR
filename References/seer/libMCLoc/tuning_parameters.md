# libMCLoc.so 튜닝 파라미터 전수 추출 (2026-06-24)

대상: `/media/.../SeerRobotics/rbk/plugins/libMCLoc.so` (ELF, not stripped, DWARF 보유)

추출원: `MCLoc::loadFromConfigFile()` (0x1ea7c0~0x1f348e) 내 92개 `loadParam` 호출. objdump 디스어셈블 + .rodata 상수풀(objdump -s) 정적 추적.

- default/min/max: double=xmm0/xmm1/xmm2 movsd 상수(.rodata), int=ecx/r8d/r9d 즉치, bool=ecx 즉치. (전수 확인)
- name/desc: rdx(name)/r8|r9(desc) 가 가리키는 std::string. 식별자형=name, 문장형=desc 로 분류.
- min=±1.79e308 은 DBL_MAX (범위 미지정), int min/max=±2147483648/2147483647 은 INT_MIN/MAX (범위 미지정).

| # | name | type | default | min | max | description | call addr |
|---|------|------|---------|-----|-----|-------------|-----------|
| 0 | update_mode_info | bool | 1 | - | - | update mode info record | 0x1ea87b |
| 1 | useUndistortion | bool | 1 | - | - | Use laser undistortioni | 0x1ea934 |
| 2 | useOpticalMotion | bool | 0 | - | - | Use optical motion track localization | 0x1ea9fb |
| 3 | useRTKLocalization | bool | 1 | - | - | use RTK Localization | 0x1eaab6 |
| 4 | RTKWeight | double | 0.05 | 0 | 1 | rtk particles weight | 0x1eab76 |
| 5 | 3DLocType | int | 0 | 0 | 1 | 3D Localization Type(Need Reboot) | 0x1eac33 |
| 6 | 3DLocalizationWeight | double | 0.1 | 0 | 1 | 3D Localization weight | 0x1ead10 |
| 7 | 3DSourceDownSize | double | 0.3 | 0.05 | 1 | 3D Points DownSample Size | 0x1eade3 |
| 8 | NDTResolution | double | 1.5 | 0.5 | 10 |  | 0x1eaea2 |
| 9 | NDTUpdateTimeThd | int | 80 | 10 | 500 | NDT Update Time Thd(ms) | 0x1eaf69 |
| 10 | 3DScoreDistance | double | 0.1 | 0.01 | 1 | 3D Score Distance | 0x1eb03d |
| 11 | PatLogSkip | int | 10 | 1 | 40 |  | 0x1eb0e7 |
| 12 | FeatureLocEnable | bool | 0 | - | - | enable feature loc | 0x1eb19b |
| 13 | FeaturesValidRange | double | 10 | 0.1 | 200 | Features Valid Range | 0x1eb270 |
| 14 | FeaturesLocRotateThd | double | 10 | 0 | 180 | Features Loc Rotate Thd | 0x1eb348 |
| 15 | ParticleMoveRadius | double | 10 | 1 | 5000 | Particle move radius (mm) | 0x1eb424 |
| 16 | ParticleExtraMoveRadius | double | 40 | 0 | 5000 | Particle extra move radius (mm) | 0x1eb503 |
| 17 | ParticleExtraMoveAngle | double | 3 | 0 | 360 | Particle extra move angle (deg) | 0x1eb5e2 |
| 18 | SlamRegion | bool | 0 | - | - | The map points in current slam region is using by SLAM | 0x1eb6af |
| 19 | LogPosInterval | int | 5 | 1 | 100 | The time interval of recording localization info (s) | 0x1eb787 |
| 20 | CheckDistance | double | 1 | 0.1 | 10 | The distance threshold of recovering in normal mode without using skiding mode (m) | 0x1eb886 |
| 21 | CheckAngle | double | 30 | 0.01 | 180 | The angle threshold of recovering in normal mode without using skiding mode (degree) | 0x1eb979 |
| 22 | ForceExtraMove | bool | 0 | - | - | check if force extra move | 0x1eba2f |
| 23 | ForceExtraMoveDist | double | 10 | 0 | 1000 | The distance of force extra move (mm) | 0x1ebb14 |
| 24 | ForceExtraMoveAngle | double | 2 | 0 | 360 | The angle of force extra move (degree) | 0x1ebc03 |
| 25 | Type | int | 0 | 0 | 1 | The type of reflector: Type = 0--circle,Type = 1--plane | 0x1ebccc |
| 26 | Number | int | 5 | 1 | 1000 | The minimum number of detecting reflector in map | 0x1ebd8e |
| 27 | Width | double | 0.08 | 0 | 1 | The width or diameter of reflector | 0x1ebe53 |
| 28 | UseRssiCenter | bool | 1 | - | - | use laser rssi to calculate center | 0x1ebf0f |
| 29 | ClusteringWidth | double | 0.2 | 0.1 | 10 | The mininum number of clustering reflector points | 0x1ebff7 |
| 30 | BeamsNumUsedInLoc | int | 541 | 0 | 100000 | The number of laser beams used in Localization | 0x1ec0cf |
| 31 | ReflectorRSSI | double | 150 | 1 | 255 | The rssi threshold of detecting reflector | 0x1ec1b2 |
| 32 | ReflectorOptimization | bool | 0 | - | - | Whether to use reflector triangulation | 0x1ec287 |
| 33 | deltaRSSI | double | 30 | 0 | 100 | The increment of RSSI | 0x1ec34b |
| 34 | 불확실 | bool | 0 | - | - | Set error if not enough reflectors can be detected | 0x1ec3f7 |
| 35 | 불확실 | bool | 1 | - | - | automatic localization in Tag | 0x1ec492 |
| 36 | WarningDistance | double | 2 | 0.1 | 9999 | The distance threshold of setting error if tag cannot be seen | 0x1ec57b |
| 37 | TimeDelay | double | 0 | 0 | 9999 |  | 0x1ec622 |
| 38 | sleepTime | double | 10 | 5 | 1000 |  | 0x1ec6d3 |
| 39 | recoverTime | double | 1 | 0 | 1000 | The time interval of recovering after stop caused by skidding | 0x1ec7ab |
| 40 | lowSpeedMoveRadius | double | 10 | 1 | 1000 | The particle move radius in low speed | 0x1ec895 |
| 41 | lowSpeedMoveAngle | double | 1 | 0 | 1000 | The particle move angle in low speed | 0x1ec974 |
| 42 | GridRelocMapGaussianDist | int | 100 | -2147483648 | 2147483647 |  | 0x1eca1c |
| 43 | UseOpenCLWithPF | bool | 0 | - | - | whether to Use OpenCL with PF | 0x1ecad8 |
| 44 | ScanLostTimeThresh | int | 300 | 0 | 10000 | The time threshold in receiving odometer by localization(ms) | 0x1eccbd |
| 45 | OdoLostTimeThresh | int | 300 | 0 | 10000 | The time threshold in receiving laser scan by localization(ms) | 0x1ecda5 |
| 46 | MutableMinParticleNumber | int | 500 | 100 | 2000 | The number of particles in localization | 0x1ece8a |
| 47 | InitParticleNumber | int | 10000 | -2147483648 | 2147483647 |  | 0x1ecf34 |
| 48 | MutableDownSampleCount | int | 5 | 1 | 10 |  | 0x1ecfdb |
| 49 | ScanLostTimeThresh | int | 300 | 0 | 10000 | The time threshold in receiving odometer by localization(ms) | 0x1ed0bf |
| 50 | OdoLostTimeThresh | int | 300 | 0 | 10000 | The time threshold in receiving laser scan by localization(ms) | 0x1ed1a2 |
| 51 | MutableMinParticleNumber | int | 500 | 100 | 2000 | The number of particles in localization | 0x1ed287 |
| 52 | InitParticleNumber | int | 10000 | -2147483648 | 2147483647 |  | 0x1ed331 |
| 53 | MutableDownSampleCount | int | 5 | 1 | 10 |  | 0x1ed3d8 |
| 54 | MutableMaxParticleNumber | int | 3000 | 500 | 5000 | The maximum num of particles in relocalization | 0x1ed4b5 |
| 55 | MotorStopThreshold | double | 0.02 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ed568 |
| 56 | LaserBlurSigma | double | 80 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ed60d |
| 57 | LaserCloserDist | double | 0.01 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ed6b2 |
| 58 | LaserFarDist | double | 300 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ed750 |
| 59 | LaserForward | bool | 1 | - | - |  | 0x1ed7d4 |
| 60 | InitParticleDistScatter | double | 700 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ed88a |
| 61 | InitParticleAngleScatter | double | 180 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ed946 |
| 62 | DownSampleCount | int | 5 | -2147483648 | 2147483647 |  | 0x1ed9e6 |
| 63 | OdoDistError | double | 0.05 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1eda8c |
| 64 | OdoAngleError | double | 0.7 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1edb3a |
| 65 | UseOdoVxVyVRotate | int | 0 | -2147483648 | 2147483647 |  | 0x1edbe1 |
| 66 | BestParticleTolerantThreshold | double | 0.8 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1edca3 |
| 67 | ParticleWeightBeginToMove | double | 0.9 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1edd5f |
| 68 | MaxParticleNumber | int | 3000 | -2147483648 | 2147483647 |  | 0x1ede06 |
| 69 | MinParticleNumber | int | 500 | -2147483648 | 2147483647 |  | 0x1edead |
| 70 | AdaptiveSampleNumberXYStep | int | 100 | -2147483648 | 2147483647 |  | 0x1edf5b |
| 71 | GridMapGaussianDistMutable | int | 20 | 1 | 1000 | Gauss dist for gridMap | 0x1ee037 |
| 72 | GridOdoMapGaussianDist | int | 255 | -2147483648 | 2147483647 |  | 0x1ee0ed |
| 73 | StopRelocWeightThreshold | double | 1 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ee1ab |
| 74 | ExtraMoveDistThreshold | double | 20 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ee257 |
| 75 | ExtraMoveAngleThreshold | double | 1 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ee303 |
| 76 | StopInitialLocWeightThreshold | double | 1 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1ee3b6 |
| 77 | OnlyOdoLikelihoodThreshold | double | 0 | 0 | 1 | The confidence threshold to change into odometer mode | 0x1ee4a6 |
| 78 | RefLikelihoodThreshold | double | 0.95 | 0 | 1 | The confidence threshold to change into reflector mode | 0x1ee594 |
| 79 | StopRelocWhenOdoStop | bool | 1 | - | - | Stop use particle filter localization if stop from odometer | 0x1ee670 |
| 80 | GridSize | int | 10 | 10 | 20 |  | 0x1ee704 |
| 81 | MutablePfThreadNum | int | 4 | 1 | 6 | The number of thread used by particle filter localization | 0x1ee7ee |
| 82 | QuadTreeResolution | int | 500 | -2147483648 | 2147483647 |  | 0x1ee942 |
| 83 | GridIGNORE | int | -1 | -2147483648 | 2147483647 |  | 0x1ee9d0 |
| 84 | LaserLookUpTableAngleResolution | double | 0.5 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1eea83 |
| 85 | LaserLookUpTableRange | double | 80 | -1.7976931348623157e+308 | 1.7976931348623157e+308 |  | 0x1eeb3f |
| 86 | LoadMapThreadNum | int | 4 | -2147483648 | 2147483647 |  | 0x1eebd8 |
| 87 | ScanLostTimeThresh | int | 500 | 0 | 10000 | The time threshold in receiving odometer by localization(ms) | 0x1f0c84 |
| 88 | OdoLostTimeThresh | int | 500 | 0 | 10000 | The time threshold in receiving laser scan by localization(ms) | 0x1f0d6c |
| 89 | MutableMinParticleNumber | int | 250 | 100 | 2000 | The number of particles in localization | 0x1f0e51 |
| 90 | InitParticleNumber | int | 3000 | -2147483648 | 2147483647 |  | 0x1f0efb |
| 91 | MutableDownSampleCount | int | 2 | 1 | 10 |  | 0x1f0fa2 |
