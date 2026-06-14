Name:           theflow
Version:        0.1.0
Release:        1%{?dist}
Summary:        theFlow! — Visual Canvas Application
License:        GPLv3
URL:            https://github.com/xaviergares/theflow

# The PyInstaller-built binary tarball.
# Build it first:  pyinstaller theflow_linux.spec
# Then package:    tar -czf theflow-0.1.0.tar.gz -C dist theflow
Source0:        theflow-%{version}.tar.gz

# Icon and desktop file (kept in the project root)
Source1:        icons/icon.png
Source2:        theflow.desktop

BuildArch:      x86_64

# PyInstaller bundles everything — no Python/Qt deps needed at runtime
AutoReqProv:    no

%description
theFlow! is a visual node-based canvas application for organising
images, video, audio, documents and notes in a freeform flow graph.
Built with PyQt6 and bundled as a self-contained binary.

# ── Prep ──────────────────────────────────────────────────────────
%prep
%setup -q -c -n %{name}-%{version}
# Source0 unpacks the single 'theflow' binary into the build dir

# ── Build ─────────────────────────────────────────────────────────
%build
# Nothing to compile — binary is pre-built by PyInstaller

# ── Install ───────────────────────────────────────────────────────
%install
# Binary
install -Dm755 theflow %{buildroot}/usr/bin/theflow

# Icon  (256×256 PNG)
install -Dm644 %{SOURCE1} %{buildroot}/usr/share/icons/hicolor/256x256/apps/theflow.png

# Desktop entry
install -Dm644 %{SOURCE2} %{buildroot}/usr/share/applications/theflow.desktop

# Documentation
install -Dm644 %{_sourcedir}/../documentation/theFlow_manual.html \
               %{buildroot}/usr/share/doc/theflow/theFlow_manual.html

# ── Post-install: refresh icon cache & desktop DB ─────────────────
%post
/usr/bin/update-desktop-database &>/dev/null || :
/usr/bin/gtk-update-icon-cache -f -t /usr/share/icons/hicolor &>/dev/null || :

%postun
/usr/bin/update-desktop-database &>/dev/null || :
/usr/bin/gtk-update-icon-cache -f -t /usr/share/icons/hicolor &>/dev/null || :

# ── File manifest ─────────────────────────────────────────────────
%files
%license /usr/share/doc/theflow/theFlow_manual.html
/usr/bin/theflow
/usr/share/icons/hicolor/256x256/apps/theflow.png
/usr/share/applications/theflow.desktop
%dir /usr/share/doc/theflow
/usr/share/doc/theflow/theFlow_manual.html

%changelog
* Sun Jun 08 2026 Xavier Gares <theflow!@protonmail.com> - 0.1.0-1
- Initial RPM release
