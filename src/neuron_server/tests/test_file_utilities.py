"""Tests for file_utilities module."""

import hashlib
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from werkzeug.exceptions import BadRequest

from neuron_server.util.file_utilities import process_uploaded_file


@pytest.fixture
def mock_file_storage() -> Mock:
    """Create a mock FileStorage object."""
    file_storage = Mock()
    file_storage.filename = "test_image.jpg"
    file_storage.read = Mock(return_value=b"test file content")
    return file_storage


@pytest.fixture
def mock_config() -> Mock:
    """Create a mock config object."""
    config = Mock()
    config.allowed_file_types = [
        ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf", ".txt"
    ]
    config.max_file_size = 10 * 1024 * 1024  # 10MB
    config.static_folder = "/tmp/test_static"
    config.static_content_url = "http://example.com/static"
    return config


@pytest.fixture
async def cleanup_test_files() -> AsyncGenerator[None, None]:
    """Cleanup test files after tests."""
    yield
    # Cleanup any created test files
    test_dir = Path("/tmp/test_static/user")
    if test_dir.exists():
        for file in test_dir.glob("*"):
            file.unlink()
        test_dir.rmdir()


@pytest.mark.asyncio
class TestProcessUploadedFile:
    """Test cases for process_uploaded_file function."""

    async def test_process_valid_jpg_file(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test processing a valid JPG file."""
        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.create_thumbnails")
            as mock_create_thumbnails,
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Verify the file was read
            mock_file_storage.read.assert_called_once()

            # Verify return values
            assert ext == ".jpg"
            assert url.startswith("http://example.com/static/user/")
            assert url.endswith(".jpg")
            assert os.path.isabs(file_path)

            # Verify thumbnail creation was called
            mock_create_thumbnails.assert_called_once_with(file_path)

            # Verify file was saved
            assert os.path.exists(file_path)
            with open(file_path, "rb") as f:
                assert f.read() == b"test file content"

    async def test_process_invalid_file_type(
        self, mock_file_storage: Mock, mock_config: Mock
    ) -> None:
        """Test processing a file with invalid extension."""
        mock_file_storage.filename = "test.exe"

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            pytest.raises(BadRequest, match="Invalid file type: .exe"),
        ):
            await process_uploaded_file(mock_file_storage)

    async def test_process_file_too_large(
        self, mock_file_storage: Mock, mock_config: Mock
    ) -> None:
        """Test processing a file that exceeds size limit."""
        # Create content larger than max_file_size
        large_content = b"x" * (mock_config.max_file_size + 1)
        mock_file_storage.read.return_value = large_content

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            pytest.raises(BadRequest, match="File too large"),
        ):
            await process_uploaded_file(mock_file_storage)

    async def test_process_file_without_extension(
        self, mock_file_storage: Mock, mock_config: Mock
    ) -> None:
        """Test processing a file without extension."""
        mock_file_storage.filename = "test_file"

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            pytest.raises(BadRequest, match="Invalid file type: None"),
        ):
            await process_uploaded_file(mock_file_storage)

    async def test_process_heic_file_conversion(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test processing and converting HEIC file to JPEG."""
        mock_file_storage.filename = "test_image.heic"

        # Mock PIL Image operations
        mock_image = Mock(spec=Image.Image)
        mock_image.info = {"exif": b"mock_exif_data"}

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.Image.open",
                  return_value=mock_image),
            patch("neuron_server.util.file_utilities.create_thumbnails")
            as mock_create_thumbnails,
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Verify conversion happened
            assert ext == ".jpg"
            assert file_path.endswith(".jpg")
            assert url.endswith(".jpg")

            # Verify image was saved with correct parameters
            mock_image.save.assert_called_once_with(
                file_path, format="JPEG", quality=95, exif=b"mock_exif_data"
            )

            # Verify thumbnail creation was called
            mock_create_thumbnails.assert_called_once_with(file_path)

    async def test_process_heif_file_conversion(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test processing and converting HEIF file to JPEG."""
        mock_file_storage.filename = "test_image.heif"

        # Mock PIL Image operations
        mock_image = Mock(spec=Image.Image)
        mock_image.info = {}  # No EXIF data

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.Image.open",
                  return_value=mock_image),
            patch("neuron_server.util.file_utilities.create_thumbnails")
            as mock_create_thumbnails,
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Verify conversion happened
            assert ext == ".jpg"
            assert file_path.endswith(".jpg")
            assert url.endswith(".jpg")

            # Verify image was saved without EXIF data
            mock_image.save.assert_called_once_with(
                file_path, format="JPEG", quality=95, exif=None
            )

            # Verify thumbnail creation was called
            mock_create_thumbnails.assert_called_once_with(file_path)

    async def test_process_duplicate_file(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test processing a file that already exists (same hash)."""
        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.create_thumbnails")
            as mock_create_thumbnails,
        ):
            # First upload
            file_path1, ext1, url1 = await process_uploaded_file(mock_file_storage)

            # Reset the mock for second call
            mock_file_storage.read.return_value = b"test file content"
            mock_create_thumbnails.reset_mock()

            # Second upload with same content
            file_path2, ext2, url2 = await process_uploaded_file(mock_file_storage)

            # Should return same path and URL
            assert file_path1 == file_path2
            assert url1 == url2
            assert ext1 == ext2

            # Thumbnail creation should only be called once (first time)
            mock_create_thumbnails.assert_not_called()

    async def test_process_pdf_file(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test processing a PDF file (no thumbnail creation)."""
        mock_file_storage.filename = "document.pdf"

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.create_thumbnails")
            as mock_create_thumbnails,
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Verify return values
            assert ext == ".pdf"
            assert url.endswith(".pdf")

            # Verify thumbnail creation was NOT called for PDF
            mock_create_thumbnails.assert_not_called()

    async def test_process_png_file(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test processing a PNG file."""
        mock_file_storage.filename = "test_image.png"

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.create_thumbnails")
            as mock_create_thumbnails,
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Verify return values
            assert ext == ".png"
            assert url.endswith(".png")

            # Verify thumbnail creation was called
            mock_create_thumbnails.assert_called_once_with(file_path)

    async def test_process_webp_file(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test processing a WebP file."""
        mock_file_storage.filename = "test_image.webp"

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.create_thumbnails")
            as mock_create_thumbnails,
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Verify return values
            assert ext == ".webp"
            assert url.endswith(".webp")

            # Verify thumbnail creation was called
            mock_create_thumbnails.assert_called_once_with(file_path)

    async def test_file_hash_generation(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test that file hash is correctly generated and used in filename."""
        test_content = b"specific test content"
        mock_file_storage.read.return_value = test_content

        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.create_thumbnails"),
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Extract filename from path
            filename = os.path.basename(file_path)

            # Verify hash is in filename
            assert filename == f"{expected_hash}.jpg"

    async def test_directory_creation(
        self, mock_file_storage: Mock, mock_config: Mock, cleanup_test_files: None
    ) -> None:
        """Test that directories are created if they don't exist."""
        # Use a non-existent directory
        mock_config.static_folder = "/tmp/test_new_dir/static"

        with (
            patch("neuron_server.util.file_utilities.neuron_config", mock_config),
            patch("neuron_server.util.file_utilities.create_thumbnails"),
        ):
            file_path, ext, url = await process_uploaded_file(mock_file_storage)

            # Verify directory was created
            assert os.path.exists(os.path.dirname(file_path))

            # Cleanup
            os.unlink(file_path)
            os.rmdir(os.path.dirname(file_path))
            os.rmdir(os.path.dirname(os.path.dirname(file_path)))
