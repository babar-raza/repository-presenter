# key: imaging-readme-Imaging-NET
# repository clone: Aspose.Imaging-FOSS-for-.NET
# head: 6ebb2091ad016a46489bef65eaad0f1eb9843e1a
# utc: 2026-10-11T18:24:08Z

$ grep -n -i 'dotnet add\|nuget.org\|Aspose.Imaging.Foss' README.md | head -6 | cut -c1-200; echo grep-exit=$?
[exit 0]
1:# Aspose.Imaging FOSS for .NET
3:[![CI](https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET/actions/workflows/ci.yml/badge.svg)](https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET/actions/workflows/
5:[![Aspose.Imaging FOSS for .NET](https://products.aspose.org/media/imaging/net/banner-readme.png)](https://products.aspose.org/imaging/net/)
7:Aspose.Imaging FOSS for .NET is a free, open-source .NET library — an Aspose.Imaging
40:  PRODUCT["Aspose.Imaging FOSS for .NET"]
114:git clone https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET.git
grep-exit=0

$ git log -1 --format='%h %ad %s' --date=short
[exit 0]
6ebb209 2026-10-10 Refresh README: verified examples and documentation links (#2)
