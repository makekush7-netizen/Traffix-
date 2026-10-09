const {
  withAndroidManifest,
  withAppBuildGradle,
} = require("expo/config-plugins");
module.exports = (config) => {
  config = withAndroidManifest(config, (config) => {
    // Local demonstration builds connect to an authenticated LAN/USB host.
    // The client refuses cleartext internet endpoints; production must use HTTPS.
    config.modResults.manifest.application[0].$[
      "android:usesCleartextTraffic"
    ] = "true";
    return config;
  });
  return withAppBuildGradle(config, (config) => {
    // CMake hashes object names to avoid Ninja's Windows 260-character limit.
    // https://cmake.org/cmake/help/latest/variable/CMAKE_OBJECT_PATH_MAX.html
    if (!config.modResults.contents.includes("CMAKE_OBJECT_PATH_MAX"))
      config.modResults.contents = config.modResults.contents.replace(
        "defaultConfig {",
        'defaultConfig {\n        externalNativeBuild { cmake { arguments "-DCMAKE_OBJECT_PATH_MAX=256" } }',
      );
    if (!config.modResults.contents.includes('buildStagingDirectory'))
    config.modResults.contents = config.modResults.contents.replace('android {', 'android {\n    externalNativeBuild { cmake { buildStagingDirectory rootProject.file("../cx") } }');
  // Autolinked libraries use real paths. Codegen must use that same drive.
    config.modResults.contents = config.modResults.contents.replace(
      "\"require.resolve('react-native/package.json')\"",
      "\"require('fs').realpathSync.native(require.resolve('react-native/package.json'))\"",
    );
    config.modResults.contents = config.modResults.contents.replace(
      "\"require.resolve('@react-native/codegen/package.json', { paths: [require.resolve('react-native/package.json')] })\"",
      "\"require('fs').realpathSync.native(require.resolve('@react-native/codegen/package.json', { paths: [require.resolve('react-native/package.json')] }))\"",
    );
    return config;
  });
};
