from app.core.sanitizer import sanitize_html


def test_sanitize_html_strips_script_tags() -> None:
    raw = "<script>alert('XSS')</script><p>Safe content</p>"
    result = sanitize_html(raw)
    assert "<script>" not in result
    assert "alert('XSS')" not in result
    assert "<p>Safe content</p>" in result


def test_sanitize_html_strips_event_handlers() -> None:
    raw = '<img src="/uploads/photo.jpg" onerror="alert(1)" onload="alert(2)" />'
    result = sanitize_html(raw)
    assert "onerror" not in result
    assert "onload" not in result
    assert 'src="/uploads/photo.jpg"' in result


def test_sanitize_html_strips_inline_onclick() -> None:
    raw = '<div onclick="alert(1)" class="content"><p>Click me</p></div>'
    result = sanitize_html(raw)
    assert "onclick" not in result
    assert 'class="content"' in result
    assert "<p>Click me</p>" in result


def test_sanitize_html_blocks_javascript_urls() -> None:
    raw = '<a href="javascript:alert(1)">Evil Link</a>'
    result = sanitize_html(raw)
    assert "javascript:" not in result
    assert "<a>Evil Link</a>" in result or "Evil Link" in result


def test_sanitize_html_blocks_data_and_vbscript_urls() -> None:
    raw = (
        '<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">Data link</a>'
        '<a href="vbscript:msgbox(1)">VBScript link</a>'
        '<img src="javascript:alert(1)" />'
    )
    result = sanitize_html(raw)
    assert "data:" not in result
    assert "vbscript:" not in result
    assert "javascript:" not in result


def test_sanitize_html_strips_mixed_case_event_handlers() -> None:
    raw = (
        '<p ONCLICK="alert(1)">Text</p>'
        '<img SRC="/uploads/pic.jpg" ONERROR="alert(2)" />'
    )
    result = sanitize_html(raw)
    assert "ONCLICK" not in result
    assert "onclick" not in result
    assert "ONERROR" not in result
    assert "onerror" not in result
    assert "<p>Text</p>" in result
    assert 'src="/uploads/pic.jpg"' in result


def test_sanitize_html_preserves_legitimate_formatting() -> None:
    raw = (
        "<h1>Headline</h1>"
        "<p>First paragraph with <strong>bold</strong> and <em>italic</em> text.</p>"
        "<ul><li>Item 1</li><li>Item 2</li></ul>"
        "<blockquote>A wise quote</blockquote>"
        '<p><a href="https://cdlb.edu.ph" target="_blank">School Website</a></p>'
    )
    result = sanitize_html(raw)
    assert "<h1>Headline</h1>" in result
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result
    assert "<ul><li>Item 1</li><li>Item 2</li></ul>" in result
    assert "<blockquote>A wise quote</blockquote>" in result
    assert 'href="https://cdlb.edu.ph"' in result
    assert 'rel="noopener noreferrer"' in result


def test_sanitize_html_preserves_tables_and_code() -> None:
    raw = (
        "<table><thead><tr><th>Header 1</th><th>Header 2</th></tr></thead>"
        "<tbody><tr><td>Cell 1</td><td>Cell 2</td></tr></tbody></table>"
        "<pre><code>console.log('hello world');</code></pre>"
    )
    result = sanitize_html(raw)
    assert "<table>" in result
    assert "<th>Header 1</th>" in result
    assert "<td>Cell 1</td>" in result
    assert "<pre><code>" in result


def test_sanitize_html_strips_dangerous_tags_and_content() -> None:
    raw = (
        "<style>body { display: none; }</style>"
        '<iframe src="https://evil.com"></iframe>'
        "<object data='evil.swf'></object>"
        "<embed src='evil.swf'>"
        "<form action='/evil'><input type='text'><button>Submit</button></form>"
        "<p>Visible Story</p>"
    )
    result = sanitize_html(raw)
    assert "<style>" not in result
    assert "display: none" not in result
    assert "<iframe>" not in result
    assert "<object>" not in result
    assert "<embed>" not in result
    assert "<form" not in result
    assert "<input" not in result
    assert "<button" not in result
    assert "<p>Visible Story</p>" in result


def test_sanitize_html_handles_empty_or_none() -> None:
    assert sanitize_html("") == ""
    assert sanitize_html(None) == ""
