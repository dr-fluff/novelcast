
from novelcast.utils.files import FileUtils


def test_story_dir_uses_suffix_when_path_is_reserved(tmp_path):
    file_utils = FileUtils(tmp_path)

    first_path = file_utils.story_dir("brianjnordon", "brianjnordon")
    second_path = file_utils.story_dir(
        "brianjnordon",
        "brianjnordon",
        reserved_paths={str(first_path)},
    )

    assert first_path != second_path
    assert second_path.name == "brianjnordon_2"
    assert second_path.parent == first_path.parent
