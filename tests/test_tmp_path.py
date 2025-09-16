import pytest

parallel_threads = [
    (1, "PASSED"),  # no parallel threads
    ("auto", "PARALLEL PASSED"),  # parallel threads
]


@pytest.mark.parametrize("parallel, passing", parallel_threads)
def test_tmp_path_is_empty(pytester: pytest.Pytester, parallel, passing):
    # ensures tmp_path is empty for each thread
    # test from (gh-109)
    pytester.makepyfile("""
        def test_tmp_path(tmp_path):
            print(tmp_path)
            assert tmp_path.exists()
            assert tmp_path.is_dir()
            assert len(list(tmp_path.iterdir())) == 0
            d = tmp_path / "sub"
            assert not d.exists()
            d.mkdir()
            assert d.exists()
    """)

    result = pytester.runpytest(f"--parallel-threads={parallel}", "-v")

    result.stdout.fnmatch_lines(
        [
            f"*::test_tmp_path {passing}*",
        ]
    )


@pytest.mark.parametrize("parallel, passing", parallel_threads)
def test_tmp_path_read_write(pytester: pytest.Pytester, parallel, passing):
    # ensures we can read/write in each tmp_path
    pytester.makepyfile("""
        def test_tmp_path(tmp_path):
            file = tmp_path / "file"
            with open(file, "w") as f:
                f.write("Hello world!")
            assert file.is_file()
            assert file.read_text() == "Hello world!"
    """)

    result = pytester.runpytest(f"--parallel-threads={parallel}", "-v")

    result.stdout.fnmatch_lines(
        [
            f"*::test_tmp_path {passing}*",
        ]
    )


@pytest.mark.parametrize("parallel, passing", parallel_threads)
def test_tmp_path_delete(pytester: pytest.Pytester, parallel, passing):
    # ensures we can delete files in each tmp_path
    pytester.makepyfile("""
        def test_tmp_path(tmp_path):
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            file = subdir / "file"
            with open(file, "w") as f:
                f.write("Hello world!")
            assert file.is_file()
            file.unlink()
            assert not file.exists()
            subdir.rmdir()
            assert not subdir.exists()
    """)

    result = pytester.runpytest(f"--parallel-threads={parallel}", "-v")

    result.stdout.fnmatch_lines(
        [
            f"*::test_tmp_path {passing}*",
        ]
    )


@pytest.mark.parametrize("parallel, passing", parallel_threads)
def test_tmpdir_is_empty(pytester: pytest.Pytester, parallel, passing):
    # ensures tmpdir is empty for each thread
    pytester.makepyfile("""
        def test_tmpdir(tmpdir):
            assert tmpdir.check()
            assert tmpdir.check(dir=1)
            assert len(list(tmpdir.listdir())) == 0
            assert not tmpdir.join("sub").check()
            assert tmpdir.mkdir("sub").check()
    """)

    result = pytester.runpytest(f"--parallel-threads={parallel}", "-v")

    result.stdout.fnmatch_lines(
        [
            f"*::test_tmpdir {passing}*",
        ]
    )


@pytest.mark.parametrize("parallel, passing", parallel_threads)
def test_tmpdir_read_write(pytester: pytest.Pytester, parallel, passing):
    # ensures we can read/write in each tmpdir
    pytester.makepyfile("""
        def test_tmpdir(tmpdir):
            file = tmpdir.join("file")
            with open(file, "w") as f:
                f.write("Hello world!")
            assert file.check(file=1)
            assert file.read_text("utf-8") == "Hello world!"
    """)

    result = pytester.runpytest(f"--parallel-threads={parallel}", "-v")

    result.stdout.fnmatch_lines(
        [
            f"*::test_tmpdir {passing}*",
        ]
    )


@pytest.mark.parametrize("parallel, passing", parallel_threads)
def test_tmpdir_delete(pytester: pytest.Pytester, parallel, passing):
    # ensures we can delete files in each tmpdir
    pytester.makepyfile("""
        def test_tmpdir(tmpdir):
            subdir = tmpdir.mkdir("sub")
            file = tmpdir.join("file")
            with open(file, "w") as f:
                f.write("Hello world!")
            assert file.check(file=1)
            file.remove()
            assert not file.check()
            subdir.remove()
            assert not subdir.check()
    """)

    result = pytester.runpytest(f"--parallel-threads={parallel}", "-v")

    result.stdout.fnmatch_lines(
        [
            f"*::test_tmpdir {passing}*",
        ]
    )


@pytest.mark.parametrize("parallel, passing", parallel_threads)
def test_tmp_path_tmpdir(pytester: pytest.Pytester, parallel, passing):
    # ensures tmp_path and tmpdir can be used at the same time
    pytester.makepyfile("""
        def test_both(tmp_path, tmpdir):
            assert tmp_path.exists()
            assert tmpdir.check(dir=1)
            assert tmp_path == tmpdir
    """)

    result = pytester.runpytest(f"--parallel-threads={parallel}", "-v")

    result.stdout.fnmatch_lines(
        [
            f"*::test_both {passing}*",
        ]
    )
