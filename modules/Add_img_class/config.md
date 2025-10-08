# Anki Image Classifier Script

This Python script batch-updates your Anki notes by automatically adding CSS classes to `<img>` tags based on each image's **native width**, **height**, and **aspect ratio**. It allows for responsive styling and better control of image formatting inside your cards.

## 📋 Features

- Automatically classifies images as:
  - `small` → width < `small_width` (default: 300)
  - `img-ultra-wide` → aspect ratio > `wide_ratio` (default: 1.9)
  - `img-landscape` → aspect ratio > `landscape_ratio_min` (default: 1.39)
  - `img-tall` → aspect ratio < `tall_ratio` (default: 0.75)
  - `img-square` → aspect ratio between `square_min` and `square_max` (defaults: 0.9–1.1)
- Merges with any existing `class` attributes on the `<img>` tag.
- Supports multiple `<img>` tags per field and note.

## 🧠 Use Case

This script is useful for users who want to:
- Apply different CSS styles to images based on their shape/size.
- Improve visual consistency in Anki cards across devices or themes.

## 🛠 Requirements

- Python 3.x
- [Pillow](https://python-pillow.org/) for image dimension parsing

### Terminal:
```
pip install pillow

```