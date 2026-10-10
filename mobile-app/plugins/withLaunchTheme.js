const { withAndroidStyles, withDangerousMod } = require("expo/config-plugins");
const fs = require("node:fs/promises");
const path = require("node:path");

// Keep this light-only preview's native launch consistent with its React UI.
// Explicit framework attributes also cover OEM Android 12 starting windows.
module.exports = (config) => {
  config = withAndroidStyles(config, (mod) => {
    for (const style of mod.modResults.resources.style || []) {
      const name = style.$.name;
      if (!["AppTheme", "Theme.App.SplashScreen"].includes(name)) continue;
      if (name === "AppTheme") style.$.parent = "Theme.AppCompat.Light.NoActionBar";
      const values = {
        "android:forceDarkAllowed": "false",
        "android:windowLightStatusBar": "true",
        "android:windowBackground": "@drawable/traffix_launch_background",
      };
      if (name === "Theme.App.SplashScreen") {
        values["android:windowSplashScreenBackground"] = "@color/splashscreen_background";
        values["android:windowSplashScreenAnimatedIcon"] = "@drawable/splashscreen_logo";
      }
      style.item = (style.item || []).filter((item) => !(item.$.name in values));
      style.item.push(...Object.entries(values).map(([name, value]) => ({ $: { name }, _: value })));
    }
    return mod;
  });
  return withDangerousMod(config, ["android", async (mod) => {
    const dir = path.join(mod.modRequest.platformProjectRoot, "app/src/main/res/drawable");
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(path.join(dir, "traffix_launch_background.xml"), `<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
  <item><shape><solid android:color="#FFFCF7" /></shape></item>
  <item android:gravity="center"><bitmap android:gravity="center" android:src="@drawable/splashscreen_logo" /></item>
</layer-list>
`);
    return mod;
  }]);
};
