# Benchmark and Sample IFC Models — Sources and Licenses

This file records the sources and licenses for optional third-party IFC models. No third-party model files
or benchmark downloader are included in this checkout. Download a model from its source only when you
need it, and retain the source attribution and license terms with any redistributed copy.

---

## 1. Axiom Synthetic Test Fixtures
- **Models:** `rev1`, `rev2`, `rev3`, and injection fixtures are generated when tests or E2E workflows run.
- **Source:** Procedural generator in `tests/fixtures/factory.py`.
- **License:** MIT License (Part of the Axiom BIM codebase, © 2026 Ayanbergen Saduakassov).
- **Scope:** 16 elements, deterministic GUIDs and property sets for end-to-end regression testing.

---

## 2. buildingSMART Certification Datasets
- **Repository:** https://github.com/buildingSMART/Certification-datasets
- **License:** Creative Commons Attribution 4.0 International (CC-BY 4.0)
- **Copyright:** © buildingSMART International Ltd.
- **License Details:** http://creativecommons.org/licenses/by/4.0/

### Models Used:
1. **Building-Architecture.ifc** (142 KB)
   - *URL:* `https://raw.githubusercontent.com/buildingSMART/Certification-datasets/main/IFC%204.0.2.1%20(IFC%204%20ADD2%20TC1)/Simple-Scene/Building-Architecture.ifc`
   - *Schema:* IFC4 ADD2 TC1
2. **Building-Structural.ifc** (185 KB)
   - *URL:* `https://raw.githubusercontent.com/buildingSMART/Certification-datasets/main/IFC%204.0.2.1%20(IFC%204%20ADD2%20TC1)/Simple-Scene/Building-Structural.ifc`
   - *Schema:* IFC4 ADD2 TC1
3. **Building-Landscaping.ifc** (1.07 MB)
   - *URL:* `https://raw.githubusercontent.com/buildingSMART/Certification-datasets/main/IFC%204.0.2.1%20(IFC%204%20ADD2%20TC1)/Simple-Scene/Building-Landscaping.ifc`
   - *Schema:* IFC4 ADD2 TC1
4. **Infra-Bridge.ifc** (1.74 MB)
   - *URL:* `https://raw.githubusercontent.com/buildingSMART/Certification-datasets/main/IFC%204.0.2.1%20(IFC%204%20ADD2%20TC1)/Simple-Scene/Infra-Bridge.ifc`
   - *Schema:* IFC4.3 / IFC4 ADD2
