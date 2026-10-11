# Images and sounds

The `.sb3` is a ZIP containing `project.json` and content-addressed asset files. Costumes and sounds are embedded; players do not need the original source asset paths.

## Costumes

```python
from pathlib import Path
from itchy.game import Costume

assets = Path(__file__).parent / "assets"
coin_costume = Costume(assets / "coin.png", center_x=20, center_y=20)
```

`Costume` accepts inline SVG text or a `Path` to SVG, PNG, JPG, or JPEG. A string is interpreted as SVG content, so use `Path` for files. The current field is named `svg` even when its value is a raster-image path.

Set rotation centers explicitly for images that are not 40×40. A sprite's `costume` is its initial image; `costumes=(...)` adds more images to the exported sprite. Runtime costume switching is not yet implemented.

The compiler reads bytes, hashes their content, embeds them once per matching asset filename, and writes references into each target's costumes. `.jpeg` becomes `.jpg` in the export.

## Sounds

```python
from itchy.game import Sound, play_sound

collect_sound = Sound("Collect", assets / "collect.wav")

Sprite(
    name="Coin",
    costume=coin_costume,
    sounds=(collect_sound,),
    scripts=(on_message(ready, play_sound(collect_sound), hide()),),
)
```

WAV and MP3 files are supported. WAV sample rate and frame count are read automatically. MP3 metadata may be supplied through `rate` and `sample_count`; the browser audio engine decodes the embedded file and updates runtime metadata.

`play_sound(sound)` starts playback; `play_sound(sound, wait=True)` waits for completion. Declare the exact sound object in the owning sprite's `sounds` tuple. Headless VM tests do not attach an audio engine; use browser tests for decoding and playback behavior.

The collectible example embeds a PNG and a generated WAV tone. These are original example assets, not downloaded Scratch character artwork.
