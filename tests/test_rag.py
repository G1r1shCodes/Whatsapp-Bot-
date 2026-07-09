"""
Unit tests for the RAG pipeline components — testing actual production
functions with proper mocking of module-level side effects.
"""

import re
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest


# ── Fixtures: import production functions with side-effects mocked ──

@pytest.fixture(scope="session")
def strip_boilerplate():
    """Import the actual _strip_boilerplate from process_data.py.

    The function is standalone (only depends on `re`), so we can import
    it without worrying about process_data's module-level I/O side effects.
    """
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "process_data_test",
        "scripts/process_data.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["process_data_test"] = mod
    # suppress top-level I/O side effects by mocking os/shutil/fitz/glob
    with (
        patch("os.makedirs"),
        patch("shutil.copy"),
        patch("glob.glob", return_value=[]),
        patch("os.walk", return_value=[]),
        patch("builtins.open"),
    ):
        spec.loader.exec_module(mod)
    return mod._strip_boilerplate


@pytest.fixture(scope="session")
def format_product_catalog():
    """Import _format_product_catalog from ai.py, suppressing ChromaDB init."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "ai_test",
        "ai.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ai_test"] = mod
    # Mock ChromaDB and embedding init to prevent model download / persistence
    with (
        patch("langchain_huggingface.HuggingFaceEmbeddings"),
        patch("langchain_community.vectorstores.Chroma"),
    ):
        spec.loader.exec_module(mod)
    return mod._format_product_catalog


# ── Tests: _strip_boilerplate ────────────────────────────────────────

class TestStripBoilerplate:
    """Tests for process_data._strip_boilerplate — removes HTML nav noise."""

    def test_removes_header_noise(self, strip_boilerplate):
        sample = (
            "Product - Kdipower info@kdipower.com +91 85959 40069 "
            "Facebook Instagram Linkedin Home About Us Our Products "
            "X Control Cables Home Control Cables "
            "Introduction KDI Power Control Cables represent a wide range..."
        )
        result = strip_boilerplate(sample)
        assert "Facebook" not in result
        assert "Instagram" not in result
        assert "X Control Cables" not in result
        assert "Introduction" in result
        assert "KDI Power Control Cables" in result

    def test_removes_header_with_ampersand(self, strip_boilerplate):
        """Section names containing '&' (e.g. 'House Wires & Cables')."""
        sample = (
            "Facebook Instagram Linkedin Home About Us "
            "X House Wires & Cables Home House Wires & Cables "
            "Introduction KDI Power HomeCab-FR wires..."
        )
        result = strip_boilerplate(sample)
        assert "Facebook" not in result
        assert "HomeCab-FR" in result

    def test_removes_footer_noise(self, strip_boilerplate):
        """Everything from 'USEFULL LINKS' onward should be stripped."""
        sample = (
            "Some real content about cables. "
            "Facebook Instagram Linkedin USEFULL LINKS About Us Our Products "
            "CONTACT US 1243, Block H Copyright © 2026 by KDI Power"
        )
        result = strip_boilerplate(sample)
        assert "USEFULL LINKS" not in result
        assert "Copyright" not in result
        assert "1243, Block H" not in result
        assert "Some real content about cables" in result

    def test_removes_cta_buttons(self, strip_boilerplate):
        """"Enquire Now" and "Connect Us" buttons should be stripped."""
        sample = (
            "This is a great cable. Enquire Now "
            "Connect Us "
            "Reach out to our sales and customer support team for expert wires and cables solutions. "
            "Thank you."
        )
        result = strip_boilerplate(sample)
        assert "Enquire Now" not in result
        assert "Connect Us" not in result
        assert "This is a great cable" in result
        assert "Thank you" in result

    def test_preserves_clean_content(self, strip_boilerplate):
        text = "KDI Power manufactures XLPE and PVC armoured cables."
        assert strip_boilerplate(text) == text

    def test_empty_input(self, strip_boilerplate):
        assert strip_boilerplate("") == ""
        assert strip_boilerplate("   ") == ""

    def test_realistic_product_page(self, strip_boilerplate):
        """Full example combining header, content, and footer noise."""
        sample = (
            "House Wires & Cables - Kdipower Kdipower info@kdipower.com +91 85959 40069 "
            "Facebook Instagram Linkedin Home About Us Our Products "
            "X House Wires & Cables Home House Wires & Cables "
            "Introduction KDI Power HomeCab-FR wires are designed for safe "
            "and reliable wiring in residential and commercial buildings. "
            "They are manufactured using 99.97% electrolytic grade copper. "
            "Enquire Now Connect Us "
            "KDI Power manufactures high-quality electrical wires and cables in India. "
            "Facebook Instagram Linkedin USEFULL LINKS About Us Our Products "
            "CONTACT US 1243, Block H, DSIDC Industrial Area "
            "Copyright © 2026 by KDI Power"
        )
        result = strip_boilerplate(sample)
        # Content preserved
        assert "KDI Power HomeCab-FR wires" in result
        assert "99.97%" in result
        assert "electrolytic grade copper" in result
        # Noise removed
        assert "Facebook" not in result
        assert "Instagram" not in result
        assert "USEFULL LINKS" not in result
        assert "Copyright" not in result
        assert "Enquire Now" not in result
        assert "Connect Us" not in result


# ── Tests: _format_product_catalog ──────────────────────────────────

class TestFormatProductCatalog:
    """Tests for ai._format_product_catalog — groups products by category."""

    def test_empty_list(self, format_product_catalog):
        assert format_product_catalog([]) == "No products currently in catalog."

    def test_single_product(self, format_product_catalog):
        products = [
            {"category": "House Wires", "name": "1.5 sq mm FR",
             "conductor": "Copper", "size": "1.5 sq mm", "core": 1,
             "price_per_meter": 15.50, "stock_status": "In Stock",
             "specifications": "Flame retardant PVC insulation"}
        ]
        result = format_product_catalog(products)
        assert "📂 House Wires:" in result
        assert "1.5 sq mm FR" in result
        assert "15.5" in result
        assert "[In Stock]" in result

    def test_multiple_categories(self, format_product_catalog):
        products = [
            {"category": "Power Cables", "name": "XLPE 4C",
             "conductor": "Aluminium", "size": "50 sq mm", "core": 4,
             "price_per_meter": 250.00, "stock_status": "In Stock",
             "specifications": ""},
            {"category": "House Wires", "name": "1.5 sq mm FR",
             "conductor": "Copper", "size": "1.5 sq mm", "core": 1,
             "price_per_meter": 15.50, "stock_status": "In Stock",
             "specifications": ""},
        ]
        result = format_product_catalog(products)
        # Alphabetically sorted categories
        assert result.index("📂 House Wires:") < result.index("📂 Power Cables:")

    def test_null_price(self, format_product_catalog):
        products = [
            {"category": "Custom", "name": "Custom Cable",
             "conductor": "Copper", "size": "Custom", "core": 3,
             "price_per_meter": None, "stock_status": "Custom Only",
             "specifications": ""}
        ]
        result = format_product_catalog(products)
        assert "Price on request" in result
        assert "[Custom Only]" in result

    def test_spec_truncation(self, format_product_catalog):
        """Specifications longer than 120 chars should be truncated."""
        long_spec = "A" * 200
        products = [
            {"category": "Test", "name": "Test Cable",
             "conductor": "Cu", "size": "1", "core": 1,
             "price_per_meter": 10, "stock_status": "In Stock",
             "specifications": long_spec}
        ]
        result = format_product_catalog(products)
        # Should have "A" * 120 in the output, not the full 200
        assert "A" * 120 in result
        assert "A" * 200 not in result


# ── Tests: _retrieve_context (mocked vectorstore) ───────────────────

class TestRetrieveContext:
    """Tests for ai._retrieve_context — MMR-based RAG retrieval.

    Note: _retrieve_context uses the module-level `vectorstore` variable,
    not a function parameter. We mock it by replacing mod.vectorstore.
    """

    @pytest.fixture(autouse=True)
    def _import_retrieve(self):
        """Import the actual _retrieve_context from ai.py.
        Sets self.mod for vectorstore mocking."""
        import importlib.util, sys

        spec = importlib.util.spec_from_file_location(
            "ai_retrieve_test",
            "ai.py",
        )
        self.mod = importlib.util.module_from_spec(spec)
        sys.modules["ai_retrieve_test"] = self.mod
        with (
            patch("langchain_huggingface.HuggingFaceEmbeddings"),
            patch("langchain_community.vectorstores.Chroma"),
        ):
            spec.loader.exec_module(self.mod)
        self.retrieve = self.mod._retrieve_context

    def _set_vectorstore(self, mock_vs):
        """Helper: set the module-level vectorstore for a test."""
        self.mod.vectorstore = mock_vs

    def test_empty_query_returns_empty(self):
        self._set_vectorstore(MagicMock())
        assert self.retrieve("", "") == ""

    def test_no_vectorstore_returns_empty(self):
        self._set_vectorstore(None)
        assert self.retrieve("cables", "cables") == ""

    def test_returns_formatted_results(self):
        vs = MagicMock()
        doc = MagicMock()
        doc.page_content = "KDI Power manufactures XLPE cables with copper conductors."
        doc.metadata = {"source": "products/power_cable", "category": "products", "section": "power_cable"}
        vs.max_marginal_relevance_search.return_value = [doc]
        self._set_vectorstore(vs)

        result = self.retrieve("xlpe cable", "xlpe cable")
        assert "[Source: Products / Power Cable]" in result
        assert "KDI Power manufactures" in result

    def test_filters_short_chunks(self):
        """Chunks < 30 chars should be excluded."""
        vs = MagicMock()
        doc = MagicMock()
        doc.page_content = "Short."
        doc.metadata = {"source": "test"}
        vs.max_marginal_relevance_search.return_value = [doc]
        self._set_vectorstore(vs)

        result = self.retrieve("cables", "cables")
        assert result == ""

    def test_fallback_to_similarity_search(self):
        """If MMR returns nothing, fall back to similarity_search."""
        vs = MagicMock()
        vs.max_marginal_relevance_search.return_value = []
        doc = MagicMock()
        doc.page_content = "Some useful technical content about cables."
        doc.metadata = {"source": "products/house_wires", "category": "products", "section": "house_wires"}
        vs.similarity_search.return_value = [doc]
        self._set_vectorstore(vs)

        result = self.retrieve("house wiring", "house wiring")
        assert "[Source: Products / House Wires]" in result

    def test_handles_exception_gracefully(self):
        """If vector search throws, return empty string without crashing."""
        vs = MagicMock()
        vs.max_marginal_relevance_search.side_effect = RuntimeError("DB down")
        self._set_vectorstore(vs)
        result = self.retrieve("cables", "cables")
        assert result == ""


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

