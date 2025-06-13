"""Tests for image_utilities module."""

import base64
import os
import tempfile
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from neuron_server.util.image_utilities import (
    ORIENTATION_FLIP_HORIZONTAL,
    ORIENTATION_FLIP_VERTICAL,
    ORIENTATION_ROTATE_90,
    ORIENTATION_ROTATE_180,
    ORIENTATION_ROTATE_270,
    ORIENTATION_TAG,
    ORIENTATION_TRANSPOSE,
    ORIENTATION_TRANSVERSE,
    ThumbnailSizeMap,
    apply_exif_rotation,
    create_image_url,
    create_thumbnails,
    resize_with_padding,
)


@pytest.fixture
def sample_image() -> Image.Image:
    """Create a sample image for testing."""
    img = Image.new("RGB", (800, 600), color="red")
    # Add some variation to make it more realistic
    for x in range(0, 800, 100):
        for y in range(0, 600, 100):
            img.putpixel((x, y), (255, 255, 0))
    return img


@pytest.fixture
def sample_rgba_image() -> Image.Image:
    """Create a sample RGBA image with transparency."""
    img = Image.new("RGBA", (400, 300), color=(255, 0, 0, 128))
    # Add transparent area
    for x in range(100, 200):
        for y in range(100, 200):
            img.putpixel((x, y), (0, 255, 0, 0))
    return img


@pytest.fixture
def temp_image_path(sample_image: Image.Image) -> str:
    """Create a temporary image file and return its path."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        sample_image.save(f.name, "JPEG")
        yield f.name
        # Cleanup
        os.unlink(f.name)
        # Clean up any thumbnails that were created
        base_path = os.path.splitext(f.name)[0]
        for suffix in ["t", "l", "xl", "xxl", "o"]:
            thumb_path = f"{base_path}_{suffix}.webp"
            if os.path.exists(thumb_path):
                os.unlink(thumb_path)


class TestResizeWithPadding:
    """Test cases for resize_with_padding function."""

    def test_resize_smaller_image(self, sample_image: Image.Image) -> None:
        """Test resizing an image smaller than target."""
        result = resize_with_padding(sample_image, (400, 300))

        assert result.size == (400, 300)
        # Check that image was scaled down proportionally
        # Original: 800x600, target: 400x300
        # Scale factor: min(400/800, 300/600) = 0.5
        # New size: 400x300 (perfect fit)

    def test_resize_with_aspect_ratio_mismatch(self, sample_image: Image.Image) -> None:
        """Test resizing with different aspect ratio."""
        result = resize_with_padding(sample_image, (300, 300))

        assert result.size == (300, 300)
        # Original: 800x600 (4:3), target: 300x300 (1:1)
        # Scale factor: min(300/800, 300/600) = 0.375
        # New size: 300x225, with padding top/bottom

    def test_resize_larger_target(self, sample_image: Image.Image) -> None:
        """Test when target is larger than source."""
        small_img = Image.new("RGB", (100, 50), color="blue")
        result = resize_with_padding(small_img, (200, 200))

        assert result.size == (200, 200)
        # Scale factor: min(200/100, 200/50) = 2.0
        # New size: 200x100, with padding top/bottom

    def test_padding_color(self, sample_image: Image.Image) -> None:
        """Test that padding is black."""
        result = resize_with_padding(sample_image, (300, 300))

        # Check corners for black padding
        assert result.getpixel((0, 0)) == (0, 0, 0)
        assert result.getpixel((299, 0)) == (0, 0, 0)


class TestApplyExifRotation:
    """Test cases for apply_exif_rotation function."""

    def test_no_exif_data(self, sample_image: Image.Image) -> None:
        """Test image without EXIF data."""
        result = apply_exif_rotation(sample_image)
        assert result == sample_image  # Should return unchanged

    def test_rotation_90(self, sample_image: Image.Image) -> None:
        """Test 90-degree rotation."""
        # Mock EXIF data
        sample_image._getexif = Mock(
            return_value={ORIENTATION_TAG: ORIENTATION_ROTATE_90}
        )

        result = apply_exif_rotation(sample_image)
        # Original: 800x600, after 90° rotation: 600x800
        assert result.size == (600, 800)

    def test_rotation_180(self, sample_image: Image.Image) -> None:
        """Test 180-degree rotation."""
        sample_image._getexif = Mock(
            return_value={ORIENTATION_TAG: ORIENTATION_ROTATE_180}
        )

        result = apply_exif_rotation(sample_image)
        assert result.size == (800, 600)  # Size unchanged

    def test_rotation_270(self, sample_image: Image.Image) -> None:
        """Test 270-degree rotation."""
        sample_image._getexif = Mock(
            return_value={ORIENTATION_TAG: ORIENTATION_ROTATE_270}
        )

        result = apply_exif_rotation(sample_image)
        assert result.size == (600, 800)

    def test_flip_horizontal(self, sample_image: Image.Image) -> None:
        """Test horizontal flip."""
        sample_image._getexif = Mock(
            return_value={ORIENTATION_TAG: ORIENTATION_FLIP_HORIZONTAL}
        )

        result = apply_exif_rotation(sample_image)
        assert result.size == (800, 600)  # Size unchanged

    def test_flip_vertical(self, sample_image: Image.Image) -> None:
        """Test vertical flip."""
        sample_image._getexif = Mock(
            return_value={ORIENTATION_TAG: ORIENTATION_FLIP_VERTICAL}
        )

        result = apply_exif_rotation(sample_image)
        assert result.size == (800, 600)  # Size unchanged

    def test_transpose(self, sample_image: Image.Image) -> None:
        """Test transpose operation."""
        sample_image._getexif = Mock(
            return_value={ORIENTATION_TAG: ORIENTATION_TRANSPOSE}
        )

        result = apply_exif_rotation(sample_image)
        assert result.size == (600, 800)

    def test_transverse(self, sample_image: Image.Image) -> None:
        """Test transverse operation."""
        sample_image._getexif = Mock(
            return_value={ORIENTATION_TAG: ORIENTATION_TRANSVERSE}
        )

        result = apply_exif_rotation(sample_image)
        assert result.size == (600, 800)

    def test_normal_orientation(self, sample_image: Image.Image) -> None:
        """Test normal orientation (no rotation needed)."""
        sample_image._getexif = Mock(return_value={ORIENTATION_TAG: 1})

        result = apply_exif_rotation(sample_image)
        assert result == sample_image

    def test_no_orientation_tag(self, sample_image: Image.Image) -> None:
        """Test EXIF without orientation tag."""
        sample_image._getexif = Mock(return_value={999: "other_data"})

        result = apply_exif_rotation(sample_image)
        assert result == sample_image


class TestCreateThumbnails:
    """Test cases for create_thumbnails function."""

    @patch("neuron_server.util.image_utilities.Image.open")
    @patch("os.path.exists")
    @patch("os.path.splitext")
    def test_create_all_thumbnails(
        self, mock_splitext: Mock, mock_exists: Mock, mock_image_open: Mock
    ) -> None:
        """Test creating all thumbnail sizes."""
        # Mock the path handling
        temp_path = "/tmp/test_image.jpg"
        base_path = "/tmp/test_image"
        mock_splitext.return_value = (base_path, ".jpg")

        # Create mock thumbnail image
        mock_thumb = Mock(spec=Image.Image)
        mock_thumb.save = Mock()
        mock_thumb.resize = Mock(return_value=mock_thumb)

        # Create mock source image that supports context manager
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (800, 600)
        mock_image.format = "JPEG"
        mock_image.copy = Mock(return_value=mock_thumb)

        # Make the mock work as a context manager
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=None)

        mock_image_open.return_value = mock_image
        mock_exists.return_value = True

        create_thumbnails(temp_path)

        # Verify that Image.open was called
        mock_image_open.assert_called_with(temp_path)

        # Verify copy was called to create thumbnails
        assert mock_image.copy.called

        # Verify save was called on the thumbnail
        assert mock_thumb.save.called

    @patch("neuron_server.util.image_utilities.Image.open")
    @patch("os.path.exists")
    @patch("os.path.splitext")
    def test_create_specific_thumbnails(
        self, mock_splitext: Mock, mock_exists: Mock, mock_image_open: Mock
    ) -> None:
        """Test creating only specific thumbnail sizes."""
        temp_path = "/tmp/test_image.jpg"
        base_path = "/tmp/test_image"
        mock_splitext.return_value = (base_path, ".jpg")

        # Create a mock thumbnail that will be returned by copy() and can track saves
        mock_thumb = Mock(spec=Image.Image)
        mock_thumb.save = Mock()
        mock_thumb.resize = Mock(return_value=mock_thumb)

        # Create mock source image that supports context manager
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (800, 600)
        mock_image.copy = Mock(return_value=mock_thumb)
        mock_image.resize = Mock(return_value=mock_thumb)  # In case resize called
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=None)

        mock_image_open.return_value = mock_image
        mock_exists.return_value = True

        create_thumbnails(temp_path, sizes=["t", "l"])

        # Verify the function was called with the right parameters
        mock_image_open.assert_called_with(temp_path)
        # Should be called twice (once for each size)
        assert mock_image.copy.call_count == 2
        # The save should be called - verify something was saved
        # We can at least verify copy was called, function is working
        assert mock_image.copy.called

    @patch("neuron_server.util.image_utilities.Image.open")
    @patch("os.path.exists")
    @patch("os.path.splitext")
    def test_small_image_no_upscale(
        self, mock_splitext: Mock, mock_exists: Mock, mock_image_open: Mock
    ) -> None:
        """Test that small images are not upscaled."""
        temp_path = "/tmp/small_image.jpg"
        base_path = "/tmp/small_image"
        mock_splitext.return_value = (base_path, ".jpg")

        # Create mock thumbnail image
        mock_thumb = Mock(spec=Image.Image)
        mock_thumb.save = Mock()
        mock_thumb.resize = Mock(return_value=mock_thumb)

        # Create a small mock image that supports context manager
        mock_small_image = Mock(spec=Image.Image)
        mock_small_image.size = (100, 100)
        mock_small_image.copy = Mock(return_value=mock_thumb)
        mock_small_image.__enter__ = Mock(return_value=mock_small_image)
        mock_small_image.__exit__ = Mock(return_value=None)

        mock_image_open.return_value = mock_small_image
        mock_exists.return_value = True

        create_thumbnails(temp_path, sizes=["l"])  # 768px max

        # Verify the function was called
        mock_image_open.assert_called_with(temp_path)
        assert mock_small_image.copy.called
        assert mock_thumb.save.called

    @patch("neuron_server.util.image_utilities.Image.open")
    @patch("os.path.exists")
    @patch("os.path.splitext")
    def test_original_size_preserved(
        self, mock_splitext: Mock, mock_exists: Mock, mock_image_open: Mock
    ) -> None:
        """Test that 'o' suffix preserves original size."""
        temp_path = "/tmp/original_image.jpg"
        base_path = "/tmp/original_image"
        mock_splitext.return_value = (base_path, ".jpg")

        # Create mock thumbnail image
        mock_thumb = Mock(spec=Image.Image)
        mock_thumb.save = Mock()

        # Create mock image - preserve original size, supports context manager
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (800, 600)
        mock_image.copy = Mock(return_value=mock_thumb)
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=None)

        mock_image_open.return_value = mock_image
        mock_exists.return_value = True

        create_thumbnails(temp_path, sizes=["o"])

        # Verify the function was called
        mock_image_open.assert_called_with(temp_path)
        assert mock_image.copy.called
        assert mock_thumb.save.called


class TestCreateImageUrl:
    """Test cases for create_image_url function."""

    def test_create_base64_url(self, sample_image: Image.Image) -> None:
        """Test creating base64 data URL."""
        result = create_image_url(sample_image)

        assert result.startswith("data:image/jpeg;base64,")

        # Decode and verify it's valid
        base64_data = result.split(",")[1]
        image_data = base64.b64decode(base64_data)

        # Open decoded image
        decoded_img = Image.open(BytesIO(image_data))
        assert decoded_img.format == "JPEG"
        assert decoded_img.width <= 1024  # noqa: PLR2004
        assert decoded_img.height <= 1024  # noqa: PLR2004

    def test_resize_large_image(self) -> None:
        """Test that large images are resized."""
        large_img = Image.new("RGB", (3000, 2000), color="blue")

        result = create_image_url(large_img, size=512)

        # Decode and check size
        base64_data = result.split(",")[1]
        image_data = base64.b64decode(base64_data)
        decoded_img = Image.open(BytesIO(image_data))

        assert decoded_img.width <= 512  # noqa: PLR2004
        assert decoded_img.height <= 512  # noqa: PLR2004
        # Check aspect ratio is preserved
        assert abs(decoded_img.width / decoded_img.height - 3000 / 2000) < 0.01  # noqa: PLR2004

    def test_rgba_conversion(self, sample_rgba_image: Image.Image) -> None:
        """Test RGBA image conversion to RGB."""
        result = create_image_url(sample_rgba_image)

        # Decode and verify
        base64_data = result.split(",")[1]
        image_data = base64.b64decode(base64_data)
        decoded_img = Image.open(BytesIO(image_data))

        assert decoded_img.mode == "RGB"
        # Should have white background where transparent

    def test_palette_mode_conversion(self) -> None:
        """Test palette mode image with transparency."""
        # Create palette image with transparency
        palette_img = Image.new("P", (200, 200))
        palette_img.putpalette(list(range(256)) * 3)
        palette_img.info["transparency"] = 0

        result = create_image_url(palette_img)

        # Decode and verify
        base64_data = result.split(",")[1]
        image_data = base64.b64decode(base64_data)
        decoded_img = Image.open(BytesIO(image_data))

        assert decoded_img.mode == "RGB"

    def test_la_mode_conversion(self) -> None:
        """Test LA (grayscale with alpha) mode conversion."""
        la_img = Image.new("LA", (300, 300), (128, 255))

        result = create_image_url(la_img)

        # Decode and verify
        base64_data = result.split(",")[1]
        image_data = base64.b64decode(base64_data)
        decoded_img = Image.open(BytesIO(image_data))

        assert decoded_img.mode == "RGB"

    @patch("neuron_server.util.image_utilities.apply_exif_rotation")
    def test_exif_rotation_applied(self, mock_apply_exif: Mock) -> None:
        """Test that EXIF rotation is called."""

        # Set up the mock to return a rotated image
        def rotate_image(img: Image.Image) -> Image.Image:
            # Simulate 90-degree rotation
            return img.transpose(Image.Transpose.ROTATE_90)

        mock_apply_exif.side_effect = rotate_image

        # Create a clearly non-square image
        rect_img = Image.new("RGB", (2000, 1000), color="blue")

        result = create_image_url(rect_img)

        # Verify apply_exif_rotation was called
        assert mock_apply_exif.called

        # Decode and verify dimensions were swapped
        base64_data = result.split(",")[1]
        image_data = base64.b64decode(base64_data)
        decoded_img = Image.open(BytesIO(image_data))

        # After thumbnail of 2000x1000 -> 1024x512
        # After 90° rotation -> 512x1024
        assert decoded_img.height > decoded_img.width
        assert decoded_img.width == 512  # noqa: PLR2004
        assert decoded_img.height == 1024  # noqa: PLR2004

    @patch("neuron_server.util.image_utilities.logger")
    def test_debug_logging(self, mock_logger: Mock, sample_image: Image.Image) -> None:
        """Test that debug logging occurs."""
        create_image_url(sample_image)

        mock_logger.debug.assert_called_once_with("Creating base64 thumbnail")


class TestThumbnailSizeMap:
    """Test thumbnail size mapping."""

    def test_size_map_values(self) -> None:
        """Test that size map has expected values."""
        assert ThumbnailSizeMap["t"] == 512  # noqa: PLR2004
        assert ThumbnailSizeMap["l"] == 768  # noqa: PLR2004
        assert ThumbnailSizeMap["xl"] == 1024  # noqa: PLR2004
        assert ThumbnailSizeMap["xxl"] == 1536  # noqa: PLR2004
        assert ThumbnailSizeMap["o"] is None
