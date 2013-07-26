from collections import deque
import re
import os
import shutil
import glob
from optparse import OptionParser
import tarfile
import subprocess
import sys


def download_arxiv(arxiv_id):
    """given arxiv number, get tar.gz"""
    if "." in arxiv_id:
        url = "http://arxiv.org/e-print/" + arxiv_id
    else:
        url = "http://arxiv.org/e-print/astro-ph/" + arxiv_id

    working_dir = "./" + arxiv_id + "_render"

    subprocess.call(["wget", "--user-agent=Lynx", url])

    # the filename is just arxiv number
    tar = tarfile.open(arxiv_id)
    tar.extractall(path=working_dir)
    tar.close()
    os.remove(arxiv_id)

    return working_dir


def find_file_containing(path, fstring, extension=""):
    """find the first file in a directory containing a string"""
    filelist = glob.glob(path + '/*' + extension)
    print "searching file list: ", filelist

    for fname in filelist:
        if os.path.isfile(fname):
            print fname
            with open(fname) as f:
                for line in f:
                    if fstring in line:
                        return fname

    return None


def between_instances(lines, pattern_list, maxlen=None):
    """generator to find text between instances of a string"""
    previous_lines = deque(maxlen=maxlen)
    for line in lines:
        if any(pattern in line for pattern in pattern_list):
            # find the section heading in brackets
            rbracket = re.compile(".*?\{(.*?)\}")
            mbracket = rbracket.match(line)
            section_head = mbracket.group(1)
            section_head = section_head.replace(' ', '_')
            section_head = section_head.lower()

            yield section_head, previous_lines
            previous_lines.clear()

        previous_lines.append(line)


def clean_tex(tex_segment):
    """strip some tex for better txt conversion"""
    tex_segment = tex_segment.replace(r"\citep", r"\cite")
    tex_segment = tex_segment.replace(r"\citet", r"\cite")
    # non-greedy
    tex_segment = re.sub(r'\\cite{.*?}', '', tex_segment)
    tex_segment = re.sub(r'\\footnote{.*?}', '', tex_segment)
    tex_segment = re.sub(r'\\label{.*?}', '', tex_segment)
    tex_segment = re.sub(r'\\ref{.*?}', '', tex_segment)

    return tex_segment


def latex_to_tex_sec(filename, path="", prefix=None):
    """identify sections of a latex file and simplify them for txt conv."""
    watch = [r"\section", r"\end{document}"]
    last_heading = "header"
    counter = 0
    file_list = []

    with open(filename) as f:
        for line, prevlines in between_instances(f, watch):
            ofname = path + "/"
            if prefix is not None:
                ofname += prefix + "_"

            ofname += str(counter) + "_"
            ofname += last_heading + ".tex"

            file_list.append(ofname)
            outfile = open(ofname, "w")

            # modify citations
            sec_tex = ''.join(prevlines)
            sec_tex = clean_tex(sec_tex)
            outfile.write(sec_tex)
            outfile.close()

            last_heading = line
            counter += 1

    print "tex files for each section: ", file_list
    return file_list


def arxiv_to_speech(arxiv_id, debug=False, keyword=None):
    """render an arxiv article to speech"""
    print "starting on: ", arxiv_id

    working_dir = download_arxiv(arxiv_id)
    maintex = find_file_containing(working_dir, "\\begin{document}",
                                   extension=".tex")

    if maintex is not None:
        print "main tex file is: ", maintex
    else:
        print "error: could not find master tex file"
        sys.exit()

    prefix = "arxiv" + arxiv_id
    if keyword is not None:
        prefix += "_" + keyword

    tex_filelist = latex_to_tex_sec(maintex, path=working_dir,
                                    prefix=prefix)

    for fname in tex_filelist:
        basefile = os.path.splitext(fname)[0]
        basename = os.path.basename(basefile)
        txtname = basefile + ".txt"
        out_fname = basename + ".aac"
        os.system("detex " + fname + " > " + txtname)
        # if only aiff possible: afconvert -f mp4f -d aac in.aiff out.mp4
        if not debug:
            subprocess.call(["say", "-f", txtname, "-o", out_fname])

    if not debug:
        shutil.rmtree(working_dir)


def main():
    parser = OptionParser(usage="usage: %prog [options] filename",
                          version="%prog 1.0")

    parser.add_option("-d", "--debug",
                      action="store_true",
                      dest="debug",
                      default=False,
                      help="save only the header, intro, conclusions")

    parser.add_option("-k", "--keyword",
                      action="store",
                      dest="keyword",
                      default=None,
                      help="provide an optional keyword flag")

    (options, args) = parser.parse_args()
    optdict = vars(options)

    if len(args) != 1:
        parser.error("wrong number of arguments")

    arxiv_to_speech(args[0],
                    debug=optdict["debug"],
                    keyword=optdict["keyword"])


if __name__ == '__main__':
    main()
