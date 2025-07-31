"""Tests for media utility functions."""


from neuron_server.util.media_utilities import get_media_type_from_extension


class TestGetMediaTypeFromExtension:
    """Test media type determination from file extensions."""

    def test_image_extensions(self):
        """Test image file extensions return 'image' type."""
        image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"]
        for ext in image_extensions:
            assert get_media_type_from_extension(ext) == "image"
            # Test case insensitive
            assert get_media_type_from_extension(ext.upper()) == "image"

    def test_audio_extensions(self):
        """Test audio file extensions return 'audio' type."""
        audio_extensions = [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".webm"]
        for ext in audio_extensions:
            assert get_media_type_from_extension(ext) == "audio"

    def test_video_extensions(self):
        """Test video file extensions return 'video' type."""
        video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".flv"]
        for ext in video_extensions:
            assert get_media_type_from_extension(ext) == "video"

    def test_html_extensions(self):
        """Test HTML file extensions return 'html' type."""
        html_extensions = [".html", ".htm"]
        for ext in html_extensions:
            assert get_media_type_from_extension(ext) == "html"

    def test_code_extensions(self):
        """Test code file extensions return 'code' type."""
        code_extensions = [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c",
            ".cs", ".go", ".rb", ".php", ".swift", ".kotlin", ".scala",
            ".rust", ".rs"
        ]
        for ext in code_extensions:
            assert get_media_type_from_extension(ext) == "code"

    def test_markdown_extensions(self):
        """Test markdown file extensions return 'text' type for preview."""
        markdown_extensions = [".md", ".markdown"]
        for ext in markdown_extensions:
            assert get_media_type_from_extension(ext) == "text"

    def test_data_extensions(self):
        """Test data file extensions return 'data' type."""
        data_extensions = [
            ".txt", ".json", ".csv", ".xml", ".yaml", ".yml",
            ".toml", ".ini", ".log", ".pdf"
        ]
        for ext in data_extensions:
            assert get_media_type_from_extension(ext) == "data"

    def test_unknown_extensions(self):
        """Test unknown file extensions return 'data' type as fallback."""
        unknown_extensions = [".xyz", ".foo", ".bar", ".unknown"]
        for ext in unknown_extensions:
            assert get_media_type_from_extension(ext) == "data"

    def test_empty_extension(self):
        """Test empty extension returns 'data' type."""
        assert get_media_type_from_extension("") == "data"
        assert get_media_type_from_extension(".") == "data"
