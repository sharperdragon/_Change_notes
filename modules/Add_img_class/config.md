# Add_img_class Configuration Notes

This module adds CSS classes to `<img>` tags in selected notes based on image size and aspect ratio.

## Runtime Config Source

Settings are read from the root add-on `config.json` section:

```json
"add_img_class": {
  "small_width": 340,
  "ultra-wide_ratio": 1.89999999,
  "landscape_ratio_min": 1.1900000001,
  "tall_ratio": 0.899999,
  "square_min": 0.8999991,
  "square_max": 1.19
}
```

## Class Rules

- `small`: `width < small_width`
- `ultra-wide`: `width / height > ultra-wide_ratio`
- `img-landscape`: ratio is above `landscape_ratio_min` but not `ultra-wide`
- `img-tall`: ratio is below `tall_ratio`
- `img-square`: ratio is between `square_min` and `square_max`
- `img-default`: used when the image file is missing locally
- `larger`: optionally added when image filename appears in `larger_imgs.txt`

## Notes

- Existing class attributes are preserved, but managed image-shape classes are replaced each run.
- This module uses bundled Pillow in `modules/Add_img_class/vendor/`.
