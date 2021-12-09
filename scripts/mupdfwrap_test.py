#!/usr/bin/env python3

'''
Simple tests of the Python MuPDF API.
'''

import inspect
import os
import sys

if os.environ.get('MUPDF_PYTHON') in ('swig', None):
    # PYTHONPATH should have been set up to point to a build/shared-*/
    # directory containing mupdf.so generated by scripts/mupdfwrap.py and SWIG.
    import mupdf
elif os.environ.get('MUPDF_PYTHON') == 'cppyy':
    sys.path.insert(0, os.path.abspath(f'{__file__}/../../platform/python'))
    import mupdf_cppyy
    del sys.path[0]
    mupdf = mupdf_cppyy.cppyy.gbl.mupdf
else:
    raise Exception(f'Unrecognised $MUPDF_PYTHON: {os.environ.get("MUPDF_PYTHON")}')


_log_prefix = ''

def log(text):
    f = inspect.stack()[1]
    print(f'{f.filename}:{f.lineno} {_log_prefix}{text}', file=sys.stderr)
    sys.stderr.flush()

def log_prefix_set(prefix):
    global _log_prefix
    _log_prefix = prefix

g_test_n = 0

g_mupdf_root = os.path.abspath('%s/../..' % __file__)


def show_stext(document):
    '''
    Shows all available information about Stext blocks, lines and characters.
    '''
    for p in range(document.count_pages()):
        page = document.load_page(p)
        stextpage = mupdf.StextPage(page, mupdf.StextOptions())
        for block in stextpage:
            block_ = block.m_internal
            log(f'block: type={block_.type} bbox={block_.bbox}')
            for line in block:
                line_ = line.m_internal
                log(f'    line: wmode={line_.wmode}'
                        + f' dir={line_.dir}'
                        + f' bbox={line_.bbox}'
                        )
                for char in line:
                    char_ = char.m_internal
                    log(f'        char: {chr(char_.c)!r} c={char_.c:4} color={char_.color}'
                            + f' origin={char_.origin}'
                            + f' quad={char_.quad}'
                            + f' size={char_.size:6.2f}'
                            + f' font=('
                                +  f'is_mono={char_.font.flags.is_mono}'
                                + f' is_bold={char_.font.flags.is_bold}'
                                + f' is_italic={char_.font.flags.is_italic}'
                                + f' ft_substitute={char_.font.flags.ft_substitute}'
                                + f' ft_stretch={char_.font.flags.ft_stretch}'
                                + f' fake_bold={char_.font.flags.fake_bold}'
                                + f' fake_italic={char_.font.flags.fake_italic}'
                                + f' has_opentype={char_.font.flags.has_opentype}'
                                + f' invalid_bbox={char_.font.flags.invalid_bbox}'
                                + f' name={char_.font.name}'
                                + f')'
                            )

def test(path):
    '''
    Runs various mupdf operations on <path>, which is assumed to be a file that
    mupdf can open.
    '''
    log(f'testing path={path}')

    assert os.path.isfile(path)
    global g_test_n
    g_test_n += 1

    # See notes in mupdfwrap.py:build_swig() about buffer_extract() and
    # buffer_storage().
    #
    assert getattr(mupdf.Buffer, 'buffer_storage_raw')
    assert getattr(mupdf.Buffer, 'buffer_storage')
    b = mupdf.Buffer()
    try:
        b.buffer_storage()
    except Exception as e:
        assert 'Buffer.buffer_storage() is not available' in str(e)
    else:
        assert 0, 'Expected exception from mupdf.Buffer.buffer_storage()'

    assert getattr(mupdf.Buffer, 'buffer_extract_raw')
    assert getattr(mupdf.Buffer, 'buffer_extract')

    # Test operations using functions:
    #
    log('Testing functions.')
    log(f'    Opening: %s' % path)
    document = mupdf.open_document(path)
    log(f'    mupdf.needs_password(document)={mupdf.needs_password(document)}')
    log(f'    mupdf.count_pages(document)={mupdf.count_pages(document)}')
    log(f'    mupdf.document_output_intent(document)={mupdf.document_output_intent(document)}')

    # Test operations using classes:
    #
    log(f'Testing classes')

    document = mupdf.Document(path)
    log(f'Have created mupdf.Document for {path}')
    log(f'document.needs_password()={document.needs_password()}')
    log(f'document.count_pages()={document.count_pages()}')

    if 0:
        log(f'stext info:')
        show_stext(document)

    for k in (
            'format',
            'encryption',
            'info:Author',
            'info:Title',
            'info:Creator',
            'info:Producer',
            'qwerty',
            ):
        v = document.lookup_metadata(k)
        log(f'document.lookup_metadata() k={k} returned v={v!r}')
        if k == 'qwerty':
            assert v is None, f'v={v!r}'
        else:
            pass

    zoom = 10
    scale = mupdf.Matrix.scale(zoom/100., zoom/100.)
    page_number = 0
    log(f'Have created scale: a={scale.a} b={scale.b} c={scale.c} d={scale.d} e={scale.e} f={scale.f}')

    colorspace = mupdf.Colorspace(mupdf.Colorspace.Fixed_RGB)
    log(f'{colorspace.m_internal.key_storable.storable.refs=}')
    if 0:
        c = colorspace.clamp_color([3.14])
        log('colorspace.clamp_color returned c={c}')
    pixmap = mupdf.Pixmap(document, page_number, scale, colorspace, 0)
    log(f'Have created pixmap: {pixmap.m_internal.w} {pixmap.m_internal.h} {pixmap.m_internal.stride} {pixmap.m_internal.n}')

    filename = f'mupdf_test-out1-{g_test_n}.png'
    pixmap.save_pixmap_as_png(filename)
    log(f'Have created {filename} using pixmap.save_pixmap_as_png().')

    # Print image data in ascii PPM format. Copied from
    # mupdf/docs/examples/example.c.
    #
    samples = pixmap.samples()
    stride = pixmap.stride()
    n = pixmap.n()
    filename = f'mupdf_test-out2-{g_test_n}.ppm'
    with open(filename, 'w') as f:
        f.write('P3\n')
        f.write('%s %s\n' % (pixmap.m_internal.w, pixmap.m_internal.h))
        f.write('255\n')
        for y in range(0, pixmap.m_internal.h):
            for x in range(pixmap.m_internal.w):
                if x:
                    f.write('  ')
                offset = y * stride + x * n
                if hasattr(mupdf, 'bytes_getitem'):
                    # swig
                    f.write('%3d %3d %3d' % (
                            mupdf.bytes_getitem(samples, offset + 0),
                            mupdf.bytes_getitem(samples, offset + 1),
                            mupdf.bytes_getitem(samples, offset + 2),
                            ))
                else:
                    # cppyy
                    f.write('%3d %3d %3d' % (
                            samples[offset + 0],
                            samples[offset + 1],
                            samples[offset + 2],
                            ))
            f.write('\n')
    log(f'Have created {filename} by scanning pixmap.')

    # Generate .png and but create Pixmap from Page instead of from Document.
    #
    page = mupdf.Page(document, 0)
    separations = page.page_separations()
    log(f'page_separations() returned {"true" if separations else "false"}')
    pixmap = mupdf.Pixmap(page, scale, colorspace, 0)
    filename = f'mupdf_test-out3-{g_test_n}.png'
    pixmap.save_pixmap_as_png(filename)
    log(f'Have created {filename} using pixmap.save_pixmap_as_png()')

    # Show links
    log(f'Links.')
    page = mupdf.Page(document, 0)
    link = mupdf.load_links(page.m_internal);
    log(f'{link}')
    if link:
        for i in link:
            log(f'{i}')

    # Check we can iterate over Link's, by creating one manually.
    #
    link = mupdf.Link(mupdf.Rect(0, 0, 1, 1), "hello")
    log(f'items in <link> are:')
    for i in link:
        log(f'    {i.m_internal.refs} {i.m_internal.uri}')

    # Check iteration over Outlines. We do depth-first iteration.
    #
    log(f'Outlines.')
    def olog(text):
        if 0:
            log(text)
    num_outline_items = 0
    depth = 0
    it = mupdf.OutlineIterator(document)
    while 1:
        item = it.outline_iterator_item()
        olog(f'depth={depth} valid={item.valid()}')
        if item.valid():
            log(f'{" "*depth*4}uri={item.uri()} is_open={item.is_open()} title={item.title()}')
            num_outline_items += 1
        else:
            olog(f'{" "*depth*4}<null>')
        r = it.outline_iterator_down()
        olog(f'depth={depth} down => {r}')
        if r >= 0:
            depth += 1
        if r < 0:
            r = it.outline_iterator_next()
            olog(f'depth={depth} next => {r}')
            assert r
            if r:
                # No more items at current depth, so repeatedly go up until we
                # can go right.
                end = 0
                while 1:
                    r = it.outline_iterator_up()
                    olog(f'depth={depth} up => {r}')
                    if r < 0:
                        # We are at EOF. Need to break out of top-level loop.
                        end = 1
                        break
                    depth -= 1
                    r = it.outline_iterator_next()
                    olog(f'depth={depth} next => {r}')
                    if r == 0:
                        # There are items at this level.
                        break
                if end:
                    break
    log(f'num_outline_items={num_outline_items}')

    # Check iteration over StextPage.
    #
    log(f'StextPage.')
    stext_options = mupdf.StextOptions(0)
    page_num = 40
    try:
        stext_page = mupdf.StextPage(document, page_num, stext_options)
    except Exception:
        log(f'no page_num={page_num}')
    else:
        device_stext = mupdf.Device(stext_page, stext_options)
        matrix = mupdf.Matrix()
        page = mupdf.Page(document, 0)
        cookie = mupdf.Cookie()
        page.run_page(device_stext, matrix, cookie)
        log(f'    stext_page is:')
        for block in stext_page:
            log(f'        block:')
            for line in block:
                line_text = ''
                for char in line:
                    line_text += chr(char.m_internal.c)
                log(f'            {line_text}')

        device_stext.close_device()

    # Check copy-constructor.
    log(f'Checking copy-constructor')
    document2 = mupdf.Document(document)
    del document
    page = mupdf.Page(document2, 0)
    scale = mupdf.Matrix()
    pixmap = mupdf.Pixmap(page, scale, colorspace, 0)
    pixmap.save_pixmap_as_png('mupdf_test-out3.png')

    stdout = mupdf.Output(mupdf.Output.Fixed_STDOUT)
    log(f'{type(stdout)} {stdout.m_internal.state}')

    mediabox = page.bound_page()
    out = mupdf.DocumentWriter(filename, 'png', '', mupdf.DocumentWriter.FormatPathType_DOCUMENT)
    dev = out.begin_page(mediabox)
    page.run_page(dev, mupdf.Matrix(mupdf.fz_identity), mupdf.Cookie())
    out.end_page()

    # Check out-params are converted into python return value.
    bitmap = mupdf.Bitmap(10, 20, 8, 72, 72)
    bitmap_details = bitmap.bitmap_details()
    log(f'{bitmap_details}')
    assert list(bitmap_details) == [10, 20, 8, 12], f'bitmap_details={bitmap_details!r}'

    log(f'finished test of %s' % path)


if __name__ == '__main__':

    paths = sys.argv[1:]
    if not paths:
        paths = [
                f'{g_mupdf_root}/thirdparty/zlib/zlib.3.pdf',
                ]
    # Run test() on all the .pdf files in the mupdf repository.
    #
    for path in paths:

        log_prefix_set(f'{os.path.relpath(path, g_mupdf_root)}: ')
        try:
            test(path)
        finally:
            log_prefix_set('')

    log(f'finished')
