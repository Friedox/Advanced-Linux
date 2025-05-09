# Advanced-Linux
## Lab 1

Help alias:

![img_2.png](assets/img_2.png)

```bash
python3 bldd.py -d /usr/bin -l libc.so.6 -o report.txt
```

This command scans the /usr/bin directory to identify all executable files that depend on the libc.so.6 shared library. The utility analyzes each executable's dynamic dependencies, determines their architecture, and generates a comprehensive report saved to report.txt. The output provides a valuable system-wide view of libc.so.6 usage across different CPU architectures.
![img.png](assets/img.png)

```bash
python3 bldd.py -d /usr/bin -l libc.so.6 -o report.txt
```

![img_1.png](assets/img_1.png)

```bash
python3 bldd.py -d /usr/bin -t readelf
```

This command scans all executable files in the /usr/bin directory using the alternative "readelf" tool instead of the default "objdump" for dependency analysis. It examines all shared libraries (not filtering for specific ones) and generates a comprehensive report of all dynamic library dependencies. The report is saved to the default output file "bldd_report.txt". This command is particularly useful for comparing extraction methods or when objdump might have limitations on certain executable formats.

![img_3.png](assets/img_3.png)

```bash
python3 bldd.py -d ~/ubuntu-test -l libc.so.6 -v -f pdf -o report_all
```
![img_4.png](assets/img_4.png)
![img_5.png](assets/img_5.png)
![img_6.png](assets/img_6.png)