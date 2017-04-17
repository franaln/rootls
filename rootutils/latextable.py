import os
import sys
import shutil

class LatexTable(object):

    def __init__(self, field_names=None, env=False):
        self._field_names = []
        self._align = {}
        self._rows = []
        if field_names:
            self._field_names = field_names
        if env and env in (True, False):
            self._add_environment = True
        else:
            self._add_environment = False
        self._header = True

    def __str__(self):
        return self.get_string()

    def add_row(self, row):
        if self._field_names and len(row) != len(self._field_names):
            raise Exception('Row has incorrect number of values, (actual) %d!=%d (expected)' %(len(row),len(self._field_names)))
        if not self._field_names:
            self._header = False
            self.field_names = [('Field %d' % (n+1)) for n in range(0, len(row))]
        self._rows.append(list(row))

    def add_column(self, fieldname, column, align='c'):
        if len(self._rows) in (0, len(column)):
            self._field_names.append(fieldname)
            self._align[fieldname] = align
            for i in range(0, len(column)):
                if len(self._rows) < i+1:
                    self._rows.append([])
                self._rows[i].append(column[i])
        else:
            raise Exception("Column length %d does not match number of rows %d!" % (len(column), len(self._rows)))

    def add_line(self):
        self._rows.append([r'\hline',])

    def clear(self):
        self._rows = []
        self._field_names = []
        self._widths = []

    def get_string(self):
        if not self._rows:
            return ''

        lines = []

        # add begin environment
        if self._add_environment:
            align_str = '{' + ''.join([self._align[i] for i in self._field_names]) + '}'
            lines.append(r'\begin{tabular}' + align_str )

        # add header
        if self._header:
            lines.append('\hline')
            lines.append(' & '.join(self._field_names) + r' \\')
            lines.append('\hline')

        # add rows
        for row in self._rows:
            row = [str(i) for i in row]
            lines.append(' & '.join(row) + r' \\')

        # add end environment
        if self._add_environment:
            lines.append(r'\end{tabular}')

        return '\n'.join(lines)

    def save_tex(self, name='table'):
        fname = name if name.endswith('.tex') else '%s.tex' % name
        with open(fname, 'w') as f:
            f.write(self.get_string())

    def save_pdf(self, name='table', scale=None):

        current_dir = os.getcwd()
        tmp_dir = '/tmp/latextable'

        try:
            os.makedirs(tmp_dir)
        except OSError as exception:
            print('temp directory exists. I will replace the content...')
            pass

        os.chdir(tmp_dir)
        texfile = 'latextable.tex'
        outfile = 'latextable.pdf'
        pdffile = name + '.pdf'

        with open(texfile, 'w') as f:
            f.write(r'\documentclass{article} \usepackage{graphicx} \usepackage[landscape]{geometry} \begin{document} \pagestyle{empty}')
            f.write('\n')
            if scale is not None:
                f.write(r'\scalebox{' + str(scale).replace('\n','') + r'}{' + '\n')
            f.write(self.get_string())
            if scale is not None:
                f.write('\n}')
            f.write('\n')
            f.write(r'\end{document}')

        os.system('pdflatex {0}'.format(texfile))
        os.system('pdfcrop {0} {1}'.format(outfile, pdffile))
        shutil.copy(pdffile, current_dir)

def test():
    print('# Testing LatexTable...')

    t = LatexTable(env=True)
    t.add_column('', ['SR1','CR1', 'CR2'])
    t.add_column('Data', [0.5, 0.5, 1], align='l')
    t.add_column('MC', [0.2, 0.3,2])
    t.add_line()

    t2 = LatexTable(['Hola', 'Chau'])
    t2.add_row(['1', '2'])
    print(t2)


if __name__ == '__main__':
    test()
