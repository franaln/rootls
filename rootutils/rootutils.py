# (py)root utils

import os
import ROOT
import math
from array import array

#-----------
# Utils
#-----------
class Value(object):
    def __init__(self, mean=0.0, error=0.0):
        self.mean = mean
        self.error = error

    def __repr__(self):
        if self.mean < 0.01:
            return '{:.4f} +- {:.4f}'.format(self.mean, self.error)
        else:
            return '{:.2f} +- {:.2f}'.format(self.mean, self.error)

    def __add__(self, other):
        mean = self.mean + other.mean
        error = self.error + other.error
        return Value(mean, error)

    def __sub__(self, other):
        mean = self.mean - other.mean
        error = self.error + other.error
        return Value(mean, error)

    def __mul__(self, other):

        try:
            mean = self.mean * other.mean
            try:
                error = mean * math.sqrt((self.error/self.mean)**2 + (other.error/other.mean)**2)
            except ZeroDivisionError:
                error = 0
        except AttributeError:
            mean = self.mean * other
            error = self.error * other

        return Value(mean, error)

    def __div__(self, other):
        try:
            mean = self.mean / other.mean
        except ZeroDivisionError:
            mean = 0
        try:
            error = mean * math.sqrt((self.error/self.mean)**2 + (other.error/other.mean)**2)
        except ZeroDivisionError:
            error = 0

        return Value(mean, error)

#-----------
# Root file
#-----------
class RootFile(ROOT.TFile):
    def __init__(self, path, mode='read'):
        ROOT.TFile.__init__(self, path, mode)

        if mode in ['read', 'open'] and self.IsZombie():
            raise IOError('File does not exist')

        ROOT.SetOwnership(self, False)
        self.path = path
        self.name = self.path.split('/')[-1].replace('.root','')
        self.mode = mode

    # get objects methods
    def get(self, objname):
        obj = self.Get(objname)
        obj.SetDirectory(0)
        return obj

    # write objects methods
    def write(self, obj, name=None):
        if name is None:
            name = obj.GetName()
        else:
            obj.SetName(name)

        try:
            obj.SetDirectory(self)
        except:
            self.cd()

        if self.mode == 'update':
            obj.Write(name, ROOT.TObject.kOverwrite)
        else:
            obj.Write(name)

        try:
            obj.SetDirectory(0)
        except:
            pass

    def write_list(self, objlist):
        for obj in objlist:
            self.write(obj)

    def write_dict(self, objdict):
        for obj in objdict.itervalues():
            self.write(obj)

    # loop over objects
    def loop(self, pattern=None):
        for key in self.GetListOfKeys():
            if pattern is not None and pattern not in key.GetName():
                continue
            obj = key.ReadObj()
            yield obj

    def __del__(self):
        self.Close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.Close()


#-----------
# Histograms
#-----------
def histogram(name, nx=None, xmin=None, xmax=None, xbins=None):

    if xbins:
        hist = ROOT.TH1F(name, name, len(xbins)-1, array('d', xbins))
    elif nx is not None and xmin is not None and xmax is not None:
        hist = ROOT.TH1F(name, name, nx, xmin, xmax)

    # To not be owned by the current directory
    hist.SetDirectory(0)
    ROOT.SetOwnership(hist, False)

    # Default configuration
    hist.Sumw2()
    hist.SetStats(0)
    hist.SetTitle('')

    return hist

def histogram2d(name, nx=None, xmin=None, xmax=None, ny=None, ymin=None, ymax=None, xbins=None, ybins=None):

    if xbins is not None and ybins is not None:
        hist = ROOT.TH2F(name, name, len(xbins)-1, array('d', xbins), len(ybins)-1, array('d', ybins))
    elif nx is not None and ny is not None:
        hist = ROOT.TH2F(name, name, nx, xmin, xmax, ny, ymin, ymax)

    hist.SetDirectory(0)

    return hist

def histogram_equal_to(hist, name=None):
    if name is None:
        name = hist.GetName()
    newhist = hist.Clone(name)
    newhist.Reset()
    return newhist

def histogram_normalize(hist):
    area = hist.Integral()
    if area > 0:
        hist.Scale(1/area)

def histogram_normalize_to(hist, other, xmin=None, xmax=None):
    if xmin and xmax:
        n1 = hist.Integral(hist.FindBin(xmin), hist.FindBin(xmax))
        n2 = other.Integral(other.FindBin(xmin), other.FindBin(xmax))
    else:
        n1 = hist.Integral()
        n2 = other.Integral()
    s = n2/n1 if n1 > 0.0 else 1.0
    hist.Scale(s)
    return s

def histogram_add_overflow_bin(hist):
    """ add the overflow bin  content to
    the last bin """

    last_bin = hist.GetNbinsX()
    over_bin = last_bin + 1

    # value
    new_val = hist.GetBinContent(last_bin) + hist.GetBinContent(over_bin)
    hist.SetBinContent(last_bin, new_val)
    hist.SetBinContent(over_bin, 0.0)

    # error
    e1 = hist.GetBinError(last_bin)
    e2 = hist.GetBinError(over_bin)
    new_err = math.sqrt(e1*e1 + e2*e2)
    hist.SetBinError(last_bin, new_err)
    hist.SetBinError(over_bin, 0.0)

def histogram2d_add_overflow_bin(hist):
    """ add the overflow bin  content to
    the last bin """

    last_bin_x = hist.GetNbinsX()
    last_bin_y = hist.GetNbinsY()

    over_bin_x = last_bin_x + 1
    over_bin_y = last_bin_y + 1

    for bx in xrange(hist.GetNbinsX()):

        new_val = hist.GetBinContent(bx+1, last_bin_y) + hist.GetBinContent(bx+1, over_bin_y)
        hist.SetBinContent(bx+1, last_bin_y, new_val)
        hist.SetBinContent(bx+1, over_bin_y, 0.0)

        e1 = hist.GetBinError(bx+1, last_bin_y)
        e2 = hist.GetBinError(bx+1, over_bin_y)
        new_err = math.sqrt(e1*e1 + e2*e2)
        hist.SetBinError(bx+1, last_bin_y, new_err)
        hist.SetBinError(bx+1, over_bin_y, 0.0)

    for by in xrange(hist.GetNbinsY()):

        new_val = hist.GetBinContent(last_bin_x, by+1) + hist.GetBinContent(over_bin_x, by+1)
        hist.SetBinContent(last_bin_x, by+1, new_val)
        hist.SetBinContent(over_bin_x, by+1, 0.0)

        e1 = hist.GetBinError(last_bin_x, bx+1)
        e2 = hist.GetBinError(over_bin_x, bx+1)
        new_err = math.sqrt(e1*e1 + e2*e2)
        hist.SetBinError(last_bin_x, by+1, new_err)
        hist.SetBinError(over_bin_x, by+1, 0.0)


def histogram_scale(hist, c, e_c=None):
    """ Scale histogram by a factor with error (c +- e_c)

    * c could be a Value(), or a number
    * e_c could be a number or None.
    * If error is None and c is not a Value(), it does the same as TH1.Scale()
    """
    try:
        c, e_c = c.mean, c.error
    except AttributeError:
        pass

    if e_c is None:
        hist.Scale(c)
        return
    for b in xrange(1, hist.GetNbinsX()+1):
        n_b = hist.GetBinContent(b)
        e_b = hist.GetBinError(b)

        new_n = n_b * c

        try:
            err2 = (e_b/n_b)**2 + (e_c/c)**2
            new_e = new_n * math.sqrt(err2)
        except ZeroDivisionError:
            new_e = 0

        hist.SetBinContent(b, new_n)
        hist.SetBinError  (b, new_e)


def get_cumulative_histogram(hist, inverse_x=False, inverse_y=False):

    newhist = hist.Clone(hist.GetName())
    nx = hist.GetNbinsX()
    ny = hist.GetNbinsY()
    for bx in range(nx):
        for by in range(ny):
            if inverse_x and inverse_y:
                cum = hist.Integral(1, bx+1, 1, by+1)
            elif inverse_x:
                cum = hist.Integral(1, bx+1, by+1, ny)
            elif inverse_y:
                cum = hist.Integral(bx+1, nx, 1, by+1)
            else:
                cum = hist.Integral(bx+1, nx, by+1, ny)

            newhist.SetBinContent(bx+1, by+1, cum)

    return newhist


# Histogram Manager
class HistManager:

    def __init__(self, path=None):
        self.data = dict()
        if path is not None:
            self.load(path)

    def add(self, name, xbins, xmin, xmax):
        self.data[name] = ROOT.TH1F(name, name, xbins, xmin, xmax)
        self.data[name].Sumw2()

    def add_2d(self, name, xbins, xmin, xmax, ybins, ymin, ymax):
        self.data[name] = ROOT.TH2F(name, name, xbins, xmin, xmax, ybins, ymin, ymax)
        self.data[name].Sumw2()

    def add_profile(self, name, xbins, xmin, xmax, ymin, ymax):
        self.data[name] = ROOT.TProfile(name, name, xbins, xmin, xmax, ymin, ymax)
        self.data[name].Sumw2()

    def fill(self, name, value, weight=None):
        if weight is None:
            self.data[name].Fill(value)
        else:
            self.data[name].Fill(value, weight)

    def fill_2d(self, name, value_x, value_y, weight=None):
        if weight is None:
            self.data[name].Fill(value_x, value_y)
        else:
            self.data[name].Fill(value_x, value_y, weight)

    def fill_profile(self, name, value_x, value_y, weight):
        self.data[name].Fill(value_x, value_y, weight)

    def save(self, path):
        with RootFile(path, 'recreate') as f:
            for name, hist in sorted(self.data.iteritems()):
                f.write(hist, name)

    def load(self, path):
        with RootFile(path, 'read') as f:
            for key in f.GetListOfKeys():
                name = key.GetName()
                self.data[name] = f.get(name)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, item):
        self.data[key] = item

    def __iter__(self):
        return self.data.iteritems()


#--------
# Graphs
#--------
def sort_graph(g, sort_x=True):

    ax = array('f', [])
    ay = array('f', [])

    d = dict()
    for i in xrange(g.GetN()):

        xtmp = ROOT.Double(0)
        ytmp = ROOT.Double(0)

        g.GetPoint(i, xtmp, ytmp)
        d[xtmp] = ytmp

    if sort_x:
        for x, y in sorted(d.iteritems()):
            ax.append(x)
            ay.append(y)
    else:
        for x, y in sorted(d, key=d.get):
            ax.append(x)
            ay.append(y)

    return ROOT.TGraph(g.GetN(), ax, ay)

#-------
# Style
#-------
colourdict = {
    'orange':      '#E24A33',
    'purple':      '#7A68A6',
    'blue':        '#348ABD',
    'lblue':       '#68add5',
    'turquoise':   '#188487',
    'red':         '#A60628',
    'pink':        '#CF4457',
    'green':       '#32b43c',
    'lgreen':      '#88de8f',
    'yellow':      '#e2a233',
    'lyellow':     '#f7fab3',
    'grey':        '#838283',
    'gray':        '#838283',
}

def get_color(c):

    if not isinstance(c, str):
        return c

    if c.startswith('#'):
        colour = ROOT.TColor.GetColor(c)
    else:
        try:
            colour = ROOT.TColor.GetColor(colourdict[c])
        except KeyError:
            if '+' in c:
                col, n = c.split('+')
                colour = getattr(ROOT, col)
                colour += int(n)
            elif '-' in c:
                col, n = c.split('-')
                colour = getattr(ROOT, col)
                colour -= int(n)
            else:
                colour = getattr(ROOT, c)

    return colour

def set_palette():
    s = array('d', [0.00, 0.34, 0.61, 0.84, 1.00])
    r = array('d', [0.00, 0.00, 0.87, 1.00, 0.51])
    g = array('d', [0.00, 0.81, 1.00, 0.20, 0.00])
    b = array('d', [0.51, 1.00, 0.12, 0.00, 0.00])
    ROOT.TColor.CreateGradientColorTable(len(s), s, r, g, b, 999)
    ROOT.gStyle.SetNumberContours(999)

def set_default_style():
    set_palette()
    ROOT.gStyle.SetPadTickX(1)
    ROOT.gStyle.SetPadTickY(1)
    ROOT.gStyle.SetFrameFillColor(0)
    ROOT.gStyle.SetFrameBorderSize(0)
    ROOT.gStyle.SetFrameBorderMode(0)
    ROOT.gStyle.SetCanvasColor(0)
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetTitleBorderSize(0)
    ROOT.gStyle.SetTitleFillColor(0)
    ROOT.gStyle.SetTextFont(132)
    ROOT.gStyle.SetLegendFont(132)
    ROOT.gStyle.SetLabelFont(132, "XYZ")
    ROOT.gStyle.SetTitleFont(132, "XYZ")
    ROOT.gStyle.SetEndErrorSize(0)

def set_atlas_style():

    set_palette()

    # use plain black on white colors
    icol = 0
    ROOT.gStyle.SetFrameBorderMode(icol)
    ROOT.gStyle.SetFrameFillColor(icol)
    ROOT.gStyle.SetCanvasBorderMode(icol)
    ROOT.gStyle.SetCanvasColor(icol)
    ROOT.gStyle.SetPadBorderMode(icol)
    ROOT.gStyle.SetPadColor(icol)
    ROOT.gStyle.SetStatColor(icol)

    # set the paper & margin sizes
    ROOT.gStyle.SetPaperSize(20,26)

    # set margin sizes
    ROOT.gStyle.SetPadTopMargin(0.05)
    ROOT.gStyle.SetPadRightMargin(0.05)
    ROOT.gStyle.SetPadBottomMargin(0.16)
    ROOT.gStyle.SetPadLeftMargin(0.16)

    # set title offsets (for axis label)
    ROOT.gStyle.SetTitleXOffset(1.4)
    ROOT.gStyle.SetTitleYOffset(1.4)

    # use large fonts
    font = 42 # Helvetica
    tsize = 0.05
    ROOT.gStyle.SetTextFont(font)
    ROOT.gStyle.SetTextSize(tsize)
    #ROOT.gStyle.SetLegendTextFont(font)
    ROOT.gStyle.SetLabelFont(font, "x")
    ROOT.gStyle.SetTitleFont(font, "x")
    ROOT.gStyle.SetLabelFont(font, "y")
    ROOT.gStyle.SetTitleFont(font, "y")
    ROOT.gStyle.SetLabelFont(font, "z")
    ROOT.gStyle.SetTitleFont(font, "z")

    ROOT.gStyle.SetLabelSize(tsize, "x")
    ROOT.gStyle.SetTitleSize(tsize, "x")
    ROOT.gStyle.SetLabelSize(tsize, "y")
    ROOT.gStyle.SetTitleSize(tsize, "y")
    ROOT.gStyle.SetLabelSize(tsize, "z")
    ROOT.gStyle.SetTitleSize(tsize, "z")

    # use bold lines and markers
    ROOT.gStyle.SetMarkerStyle(20)
    ROOT.gStyle.SetMarkerSize(1.2)
    ROOT.gStyle.SetHistLineWidth(2)
    ROOT.gStyle.SetLineStyleString(2, "[12 12]")
    ROOT.gStyle.SetEndErrorSize(0.)

    # do not display any of the standard histogram decorations
    ROOT.gStyle.SetOptTitle(0)
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetOptFit(0)


def set_color(obj, color, fill=False, alpha=None):
    color = get_color(color)
    obj.SetLineColor(color)
    obj.SetMarkerColor(color)
    if fill:
        if alpha is not None:
            obj.SetFillColorAlpha(color, alpha)
        else:
            obj.SetFillColor(color)


def set_style(obj, **kwargs):

    # check if hist or graph
    is_hist = obj.InheritsFrom('TH1')

    color = kwargs.get('color', 'kBlack')
    fill = kwargs.get('fill', False)

    marker_style = kwargs.get('mstyle', 20)
    fill_style = kwargs.get('fstyle', None)
    line_style = kwargs.get('lstyle',None)

    marker_size = kwargs.get('msize', 0.8)
    line_width = kwargs.get('lwidth', 2)

    alpha = kwargs.get('alpha', None)

    # default
    obj.SetTitle('')
    if is_hist:
        obj.SetStats(0)

    # color
    set_color(obj, color, fill, alpha)

    # marker
    obj.SetMarkerStyle(marker_style)
    obj.SetMarkerSize(marker_size)

    # line
    obj.SetLineWidth(line_width)
    if line_style is not None:
        obj.SetLineStyle(line_style)

    # fill
    if fill_style is not None:
        obj.SetFillStyle(fill_style)


def canvas(name='', title='', xsize=600, ysize=600):
    if not title:
        title = name
    c = ROOT.TCanvas(name, title, xsize, ysize)
    ROOT.SetOwnership(c, False)
    return c

def canvas_ratio(name='', title='', xsize=600, ysize=600):

    c = ROOT.TCanvas()

    cup   = ROOT.TPad("u", "u", 0., 0.305, 0.99, 1)
    cdown = ROOT.TPad("d", "d", 0., 0.01, 0.99, 0.295)
    cup.SetRightMargin(0.05)
    cup.SetBottomMargin(0.005)

    cup.SetTickx()
    cup.SetTicky()
    cdown.SetTickx()
    cdown.SetTicky()
    cdown.SetRightMargin(0.05)
    cdown.SetBottomMargin(0.3)
    cdown.SetTopMargin(0.0054)
    cdown.SetFillColor(ROOT.kWhite)
    cup.Draw()
    cdown.Draw()

    return cup, cdown

def legend(xmin, ymin, xmax, ymax, columns=1):
    leg = ROOT.TLegend(xmin, ymin, xmax, ymax)
    leg.SetFillColor(0)
    leg.SetBorderSize(0)
    if columns > 1:
        leg.SetNColumns(columns)
    return leg

def draw_latex(x, y, text, size=None, ndc=False):
    l = ROOT.TLatex(x, y, text)
    ROOT.SetOwnership(l, False)

    if ndc:
        l.SetNDC()

    if size is not None:
        l.SetTextSize(size)

    l.Draw()

def draw_horizontal_line(y):

    l = ROOT.TLine(0, 220, 200, 220)
    l.SetLineStyle(2)
    l.SetLineColor(ROOT.kGray+1)
    l.Draw()

def draw_ratio_lines(ratio):

    firstbin = ratio.GetXaxis().GetFirst()
    lastbin  = ratio.GetXaxis().GetLast()
    xmax     = ratio.GetXaxis().GetBinUpEdge(lastbin)
    xmin     = ratio.GetXaxis().GetBinLowEdge(firstbin)

    lines = [None, None, None,]
    lines[0] = ROOT.TLine(xmin, 1., xmax, 1.)
    lines[1] = ROOT.TLine(xmin, 0.5,xmax, 0.5)
    lines[2] = ROOT.TLine(xmin, 1.5,xmax, 1.5)

    lines[0].SetLineWidth(1)
    lines[0].SetLineStyle(2)
    lines[1].SetLineStyle(3)
    lines[2].SetLineStyle(3)

    for line in lines:
        line.AppendPad()
        line.Draw()



#
def get_histogram(filename, treename, variable, selection='', xmin=None, xmax=None, bins=None, hist=None):

    t = ROOT.TChain(treename)
    t.Add(filename)

    hist = None
    if xmin is not None and xmax is not None and bins is not None:
        hist = histogram('htemp', bins, xmin, xmax)

    t.Draw(variable+'>>htemp', '', 'goff')

    if hist is None:
        hist = ROOT.gDirectory.Get('htemp')

    return hist.Clone()
