from nbsite.nbbuild import FixNotebookLinks


class TestFixNotebookLinks:


    def test_get_links(self):
        assert list(FixNotebookLinks._get_links('foo [a](b.ipynb) bar')) == [('[a](b.ipynb)', 'b.ipynb')]
        assert list(FixNotebookLinks._get_links('foo [a](b.md) bar')) == []