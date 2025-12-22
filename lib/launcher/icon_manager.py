"""
Icon Manager for Stream Dock Launcher
Handles loading, resizing, caching, and preparing icons for display
"""
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class IconManager:
    """Manages icons for Stream Dock buttons"""

    def __init__(self, button_size=(100, 100), rotation=0):
        """
        Initialize icon manager

        Args:
            button_size: Target size for button icons (width, height)
            rotation: Rotation angle (0° for correct orientation)
        """
        self.button_size = button_size
        self.rotation = rotation
        self.icon_cache: Dict[str, str] = {}  # path -> processed_path
        self.temp_dir = "/tmp/streamdock_icons"

        # Create temp directory for processed icons
        os.makedirs(self.temp_dir, exist_ok=True)

    def prepare_icon(self, icon_path: Optional[str], label: str = "") -> str:
        """
        Prepare an icon for display on Stream Dock

        Args:
            icon_path: Path to icon image file (or None for default)
            label: Text label to display if no icon

        Returns:
            str: Path to processed icon file ready for Stream Dock
        """
        # Check cache first
        cache_key = f"{icon_path}:{label}"
        if cache_key in self.icon_cache:
            cached_path = self.icon_cache[cache_key]
            if os.path.exists(cached_path):
                return cached_path

        # Generate icon
        if icon_path and os.path.exists(icon_path):
            processed_path = self._process_icon_file(icon_path, label)
        else:
            processed_path = self._create_default_icon(label)

        # Cache it
        self.icon_cache[cache_key] = processed_path
        return processed_path

    def _process_icon_file(self, icon_path: str, label: str = "") -> str:
        """
        Process an existing icon file

        Args:
            icon_path: Path to source icon
            label: Optional text label to overlay

        Returns:
            str: Path to processed icon
        """
        try:
            # Expand paths
            icon_path = os.path.expanduser(os.path.expandvars(icon_path))

            # Load image
            img = Image.open(icon_path)

            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize to button size
            img = img.resize(self.button_size, Image.Resampling.LANCZOS)

            # Add label if provided
            if label:
                img = self._add_label(img, label)

            # Rotate for StreamDock293
            if self.rotation:
                img = img.rotate(self.rotation)

            # Save to temp file
            output_path = os.path.join(
                self.temp_dir,
                f"icon_{hash(icon_path)}_{hash(label)}.jpg"
            )
            img.save(output_path, 'JPEG', quality=100, subsampling=0)

            logger.debug(f"Processed icon: {icon_path} -> {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to process icon {icon_path}: {e}")
            return self._create_default_icon(label)

    def _create_default_icon(self, label: str) -> str:
        """
        Create a default icon with text label

        Args:
            label: Text to display

        Returns:
            str: Path to generated icon
        """
        try:
            # Create blank image
            img = Image.new('RGB', self.button_size, color='#2a2a2a')
            draw = ImageDraw.Draw(img)

            if label:
                # Try to load a nice font
                try:
                    font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 14)
                except:
                    font = ImageFont.load_default()

                # Wrap text if too long
                words = label.split()
                lines = []
                current_line = []

                for word in words:
                    test_line = ' '.join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    if bbox[2] - bbox[0] > self.button_size[0] - 10:
                        if current_line:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                        else:
                            lines.append(word)
                    else:
                        current_line.append(word)

                if current_line:
                    lines.append(' '.join(current_line))

                # Draw text centered
                y_offset = (self.button_size[1] - len(lines) * 18) // 2

                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x = (self.button_size[0] - text_width) // 2
                    y = y_offset + i * 18
                    draw.text((x, y), line, fill='white', font=font)

            # Add border
            draw.rectangle(
                [0, 0, self.button_size[0] - 1, self.button_size[1] - 1],
                outline='#555555',
                width=2
            )

            # Rotate
            if self.rotation:
                img = img.rotate(self.rotation)

            # Save
            output_path = os.path.join(self.temp_dir, f"default_{hash(label)}.jpg")
            img.save(output_path, 'JPEG', quality=100, subsampling=0)

            return output_path

        except Exception as e:
            logger.error(f"Failed to create default icon: {e}")
            # Last resort: solid color
            img = Image.new('RGB', self.button_size, color='black')
            output_path = os.path.join(self.temp_dir, "fallback.jpg")
            img.save(output_path, 'JPEG')
            return output_path

    def _add_label(self, img: Image.Image, label: str) -> Image.Image:
        """
        Add text label to bottom of icon

        Args:
            img: Source image
            label: Text to add

        Returns:
            Image with label
        """
        draw = ImageDraw.Draw(img)

        # Semi-transparent background for text
        label_height = 20
        overlay = Image.new('RGBA', self.button_size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [0, self.button_size[1] - label_height, self.button_size[0], self.button_size[1]],
            fill=(0, 0, 0, 180)
        )
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        img = img.convert('RGB')

        # Draw text
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 10)
        except:
            font = ImageFont.load_default()

        # Truncate if too long
        if len(label) > 12:
            label = label[:10] + '..'

        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.button_size[0] - text_width) // 2
        y = self.button_size[1] - label_height + 3

        draw.text((x, y), label, fill='white', font=font)

        return img

    def find_system_icon(self, app_name: str) -> Optional[str]:
        """
        Try to find a system icon for an application

        Args:
            app_name: Application name (e.g., 'libreoffice-writer')

        Returns:
            str: Path to icon file, or None if not found
        """
        # Common icon directories
        icon_dirs = [
            '/usr/share/icons/hicolor',
            '/usr/share/pixmaps',
            '~/.local/share/icons',
        ]

        # Common icon sizes (prefer larger ones)
        sizes = ['256x256', '128x128', '96x96', '72x72', '64x64', '48x48']

        for icon_dir in icon_dirs:
            icon_dir = os.path.expanduser(icon_dir)
            if not os.path.exists(icon_dir):
                continue

            # Try with size subdirectories
            for size in sizes:
                for ext in ['.png', '.svg', '.xpm']:
                    # Try direct path
                    icon_path = os.path.join(icon_dir, size, 'apps', app_name + ext)
                    if os.path.exists(icon_path):
                        logger.info(f"Found system icon: {icon_path}")
                        return icon_path

            # Try direct in pixmaps
            for ext in ['.png', '.svg', '.xpm']:
                icon_path = os.path.join(icon_dir, app_name + ext)
                if os.path.exists(icon_path):
                    logger.info(f"Found system icon: {icon_path}")
                    return icon_path

        logger.debug(f"No system icon found for: {app_name}")
        return None

    def cleanup(self):
        """Clean up temporary icon files"""
        try:
            for filename in os.listdir(self.temp_dir):
                filepath = os.path.join(self.temp_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
            logger.info("Cleaned up temp icons")
        except Exception as e:
            logger.error(f"Failed to cleanup temp icons: {e}")
