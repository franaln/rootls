# (py)root utils

import os
import sys
import ROOT
import math
from array import array

is_py3 = (sys.version_info > (3, 0))

if not is_py3:
    range = xrange


#-----------
# Utils
#-----------

# Files, directories
def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if os.path.isdir(path):
            pass
        else:
            raise

def rmdir(path):
    import shutil
    try:
        shutil.rmtree(path)
    except OSError as exc:
        pass

class Value(object):
    def __init__(self, mean=0.0, error=0.0):
        self.mean = mean
        self.error = error

    def __repr__(self):
        if self.mean < 0.01:
            return '{:.4f} +- {:.4f}'.format(self.mean, self.error)
        else:
            return '{:.2f} +- {:.2f}'.format(self.mean, self.error)

    def __gt__(self, other):
        try:
            return self.mean > other.mean
        except:
            return self.mean > other

    def __lt__(self, other):
        try:
            return self.mean < other.mean
        except:
            return self.mean < other

    def __ge__(self, other):
        try:
            return self.mean > other.mean
        except:
            return self.mean > other

    def __le__(self, other):
        try:
            return self.mean < other.mean
        except:
            return self.mean < other

    def __add__(self, other):
        mean = self.mean + other.mean
        error = math.sqrt(self.error**2 + other.error**2)
        return Value(mean, error)

    def __sub__(self, other):
        mean = self.mean - other.mean
        error = math.sqrt(self.error**2 + other.error**2)
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
# Root file (remove?)
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
# Histograms (CLEAN)
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

    # 2D histograms
    if hist.InheritsFrom('TH2'):

        last_bin_x = hist.GetNbinsX()
        last_bin_y = hist.GetNbinsY()

        over_bin_x = last_bin_x + 1
        over_bin_y = last_bin_y + 1

        for bx in range(1, last_bin_x):

            new_val = hist.GetBinContent(bx, last_bin_y) + hist.GetBinContent(bx, over_bin_y)

            hist.SetBinContent(bx, last_bin_y, new_val)
            hist.SetBinContent(bx, over_bin_y, 0.0)

            e1 = hist.GetBinError(bx, last_bin_y)
            e2 = hist.GetBinError(bx, over_bin_y)
            new_err = math.sqrt(e1*e1 + e2*e2)
            hist.SetBinError(bx, last_bin_y, new_err)
            hist.SetBinError(bx, over_bin_y, 0.0)

        for by in range(1, last_bin_y):

            new_val = hist.GetBinContent(last_bin_x, by) + hist.GetBinContent(over_bin_x, by)
            hist.SetBinContent(last_bin_x, by, new_val)
            hist.SetBinContent(over_bin_x, by, 0.0)

            e1 = hist.GetBinError(last_bin_x, by)
            e2 = hist.GetBinError(over_bin_x, by)
            new_err = math.sqrt(e1*e1 + e2*e2)
            hist.SetBinError(last_bin_x, by, new_err)
            hist.SetBinError(over_bin_x, by, 0.0)


        # last x/y bin
        new_val = hist.GetBinContent(last_bin_x, last_bin_y) + \
                  hist.GetBinContent(over_bin_x, last_bin_y) + \
                  hist.GetBinContent(last_bin_x, over_bin_y) + \
                  hist.GetBinContent(over_bin_x, over_bin_y)

        hist.SetBinContent(last_bin_x, last_bin_y, new_val)
        hist.SetBinContent(last_bin_x, over_bin_y, 0.)
        hist.SetBinContent(over_bin_x, last_bin_y, 0.)
        hist.SetBinContent(over_bin_x, over_bin_y, 0.)

        e1 = hist.GetBinError(last_bin_x, last_bin_y)
        e2 = hist.GetBinError(over_bin_x, last_bin_y)
        e3 = hist.GetBinError(last_bin_x, over_bin_y)
        e4 = hist.GetBinError(over_bin_x, over_bin_y)

        new_err = math.sqrt(e1*e1+e2*e2+e3*e3+e4*e4)
        hist.SetBinError(last_bin_x, last_bin_y, new_err)
        hist.SetBinError(last_bin_x, over_bin_y, 0.)
        hist.SetBinError(over_bin_x, last_bin_y, 0.)
        hist.SetBinError(over_bin_x, over_bin_y, 0.)



    # 1D histogram
    else:
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


ROOT.TH1.AddOverflowBin = histogram_add_overflow_bin

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
    for b in range(1, hist.GetNbinsX()+1):
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


def merge_histograms(merge_name, merge_list):

    new_hist = merge_list[0].Clone(merge_name)
    for h in merge_list[1:]:
        new_hist.Add(h, 1)

    return new_hist

# Histogram Manager
class HistManager:

    def __init__(self, path=None):
        self.data = dict()
        if path is not None:
            self.load(path)

        self.weight = 1.0

    def set_weight(self, w):
        self.weight = w

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
        if weight is not None:
            self.data[name].Fill(value, weight)
        else:
            self.data[name].Fill(value, self.weight)

    def fill_2d(self, name, value_x, value_y, weight=None):
        if weight is not None:
            self.data[name].Fill(value_x, value_y, weight)
        else:
            self.data[name].Fill(value_x, value_y, self.weight)

    def fill_profile(self, name, value_x, value_y, weight):
        if weight is not None:
            self.data[name].Fill(value_x, value_y, weight)
        else:
            self.data[name].Fill(value_x, value_y, self.weight)


    def save(self, path):
        f = ROOT.TFile(path, 'recreate')
        f.cd()
        for name, hist in sorted(self.data.iteritems()):
            hist.Write(name)

    def load(self, path):
        f = ROOT.TFile.Open(path)
        for key in f.GetListOfKeys():
            name = key.GetName()
            self.data[name] = f.Get(name)

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
    for i in range(g.GetN()):

        xtmp = ROOT.Double(0)
        ytmp = ROOT.Double(0)

        g.GetPoint(i, xtmp, ytmp)
        d[xtmp] = ytmp

    if sort_x:
        for x, y in sorted(d.items()):
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

# def set_palette():
#     s = array('d', [0.00, 0.34, 0.61, 0.84, 1.00])
#     r = array('d', [0.00, 0.00, 0.87, 1.00, 0.51])
#     g = array('d', [0.00, 0.81, 1.00, 0.20, 0.00])
#     b = array('d', [0.51, 1.00, 0.12, 0.00, 0.00])
#     ROOT.TColor.CreateGradientColorTable(len(s), s, r, g, b, 999)
#     ROOT.gStyle.SetNumberContours(999)

def set_default_style():

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
    ROOT.gStyle.SetPalette(71)

def set_atlas_style():

    ROOT.gStyle.SetPalette(71)

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

    color = kwargs.get('color', ROOT.kBlack)
    alpha = kwargs.get('alpha', None)

    mstyle = kwargs.get('mstyle', 20)
    fstyle = kwargs.get('fstyle', None)
    lstyle = kwargs.get('lstyle',None)

    msize  = kwargs.get('msize', 0.8)
    lwidth = kwargs.get('lwidth', 2)

    fill = (kwargs.get('fill', False) or fstyle is not None)

    xtitle = kwargs.get('xtitle', None)
    ytitle = kwargs.get('ytitle', None)

    xmin = kwargs.get('xmin', None)
    xmax = kwargs.get('xmax', None)
    ymin = kwargs.get('ymin', None)
    ymax = kwargs.get('ymax', None)

    # default
    obj.SetTitle('')
    if is_hist:
        obj.SetStats(0)

    # color
    set_color(obj, color, fill, alpha)

    # marker
    obj.SetMarkerStyle(mstyle)
    obj.SetMarkerSize(msize)

    # line
    obj.SetLineWidth(lwidth)
    if lstyle is not None:
        obj.SetLineStyle(lstyle)

    # fill
    if fstyle is not None:
        obj.SetFillStyle(fstyle)

    # axis titles
    if xtitle is not None:
        obj.GetXaxis().SetTitle(xtitle)
    if ytitle is not None:
        obj.GetYaxis().SetTitle(ytitle)

    if xmin is not None and xmax is not None:
        obj.GetXaxis().SetRangeUser(xmin, xmax)
    if ymin is not None and ymax is not None:
        obj.GetYaxis().SetRangeUser(ymin, ymax)


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

def draw_horizontal_line(y): # FIX

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


#-----------------------
# Statistical functions
#-----------------------

def get_significance(s, b, sb, minb=None, mins=None):

    z = ROOT.RooStats.NumberCountingUtils.BinomialExpZ(s, b, sb)

    if minb is not None and b < minb:
        z = 0.
    if mins is not None and s < mins:
        z = 0.
    if z < 0.:
        z = 0.

    if z == float('Inf'):
        z = 0.

    return z

def get_significance_unc(s, b, sb=0.5, minb=None, mins=None):

    """
    *** OLD -> use RooStats ***
    Get significance taking into account
    the background systematic uncertainty
    (from Cowan formula) """

    try:
        s = s.mean
        b = b.mean
    except:
        pass

    s, b = float(s), float(b)

    if s < 0.00001 or b < 0.00001:
        return 0.00

    if mins is not None and s < mins:
        return 0.00
    if minb is not None and b < minb:
        return 0.00

    sb = sb * b # as default we use 50% of uncertainty for the background

    za2_p = (s + b) * ROOT.TMath.Log( ((s + b) * (b + sb**2)) / (b**2 + (s + b) * sb**2) )
    za2_m = (b**2/sb**2) * ROOT.TMath.Log( 1 + (s * sb**2)/(b * (b + sb**2)) )

    za2 = 2 * (za2_p - za2_m)

    if za2 <= 0.:
        return 0

    za = ROOT.TMath.Sqrt(za2)

    if za > 0.0:
        za = round(za, 2)
    else:
        za = 0.00

    return za


def get_sb(s, b):
    if b > 0:
        return s/ROOT.TMath.Sqrt(b)
    else:
        return 0


def pvalue(obs, exp):
    if obs > exp:
        return 1 - ROOT.Math.inc_gamma_c(obs, exp)
    else:
        return ROOT.Math.inc_gamma_c(obs+1, exp)


def zvalue(pvalue):
    return ROOT.TMath.Sqrt(2) * ROOT.TMath.ErfInverse(1. - 0.2*pvalue)


def poisson_significance(obs, exp):

    p = pvalue(obs, exp)

    if p < 0.5:
        if obs > exp:
            return zvalue(p)
        else:
            return -zvalue(p)

    return 0.0


def calc_poisson_cl_lower(q, n_obs):
    """
    Calculate lower confidence limit
    e.g. to calculate the 68% lower limit for 2 observed events:
    calc_poisson_cl_lower(0.68, 2.)
    """
    ll = 0.
    if n_obs >= 0.:
        a = (1. - q) / 2. # = 0.025 for 95% confidence interval
        ll = ROOT.TMath.ChisquareQuantile(a, 2.* n_obs) / 2.

    return ll

def calc_poisson_cl_upper(q, n_obs):
    """
    Calculate upper confidence limit
    e.g. to calculate the 68% upper limit for 2 observed events:
    calc_poisson_cl_upper(0.68, 2.)
    """
    ul = 0.
    if n_obs >= 0. :
        a = 1. - (1. - q) / 2. # = 0.025 for 95% confidence interval
        ul = ROOT.TMath.ChisquareQuantile(a, 2.* (n_obs + 1.)) / 2.

    return ul

def make_poisson_cl_errors(hist):
    """
    Make a TGraph from a TH1 with the poisson errors
    """

    x_val  = array('f')
    y_val  = array('f')
    x_errU = array('f')
    x_errL = array('f')
    y_errU = array('f')
    y_errL = array('f')

    for b in range(1, hist.GetNbinsX()+1):
        bin_content = hist.GetBinContent(b)
        if bin_content > 0.:
            bin_err_up  = calc_poisson_cl_upper(0.68, bin_content) - bin_content
            bin_err_dn  = bin_content - calc_poisson_cl_lower(0.68, bin_content)
            x_val.append(hist.GetXaxis().GetBinCenter(b))
            y_val.append(bin_content)
            y_errU.append(bin_err_up)
            y_errL.append(bin_err_dn)
            x_errU.append(hist.GetXaxis().GetBinWidth(b)/2.)
            x_errL.append(hist.GetXaxis().GetBinWidth(b)/2.)

    if len(x_val) > 0:
        data_graph = ROOT.TGraphAsymmErrors(len(x_val), x_val, y_val, x_errL, x_errU, y_errL, y_errU)
        return data_graph
    else:
        return ROOT.TGraph()




#-------
# Trees
#-------

multidraw_cxx = """

// MultiDraw.cxx (code from pwaller)
// Draws many histograms in one loop over a tree.
// A little bit like a TTree::Draw which can make many histograms

#include <TTree.h>
#include <TH1D.h>
#include <TTreeFormula.h>
#include <TStopwatch.h>

#include <iostream>

// Get an Element from an array
#define EL( type, array, index ) dynamic_cast<type *>( array->At( index ) )

void MultiDraw(TTree *tree, TObjArray *formulae, TObjArray *weights, TObjArray *hists, UInt_t list_len)
{
  Long64_t i = 0;
  Long64_t num_events = tree->GetEntries();

  Double_t value = 0, weight = 0, common_weight = 0;
  Int_t tree_number = -1;

  for (i = 0; i<num_events; i++) {

    // Display progress every 10000 events
    if (i % 100000 == 0) {
      std::cout.precision(2);
      std::cout << "Done " << (double(i) / ( double(num_events)) * 100.0f) << "%   \r";
      std::cout.flush();
    }

    if (tree_number != tree->GetTreeNumber()) {
      tree_number = tree->GetTreeNumber();
    }

    tree->LoadTree(tree->GetEntryNumber(i));

    for (UInt_t j=0; j<list_len; j++) {
      // If the Value or the Weight is the same as the previous, then it can be re-used.
      // In which case, this element fails to dynamic_cast to a formula, and evaluates to NULL
      if ( EL(TTreeFormula, formulae, j) )
        value = EL(TTreeFormula, formulae, j)->EvalInstance();

      if ( EL(TTreeFormula, weights, j) )
        weight = EL(TTreeFormula, weights, j)->EvalInstance();

      if (weight)
        EL(TH1D, hists, j)->Fill(value, weight);
    }
  }
}
"""


def MakeTObjArray(the_list):
    """
    Turn a python iterable into a ROOT TObjArray
    """

    result = ROOT.TObjArray()
    result.SetOwner()

    # Make PyROOT give up ownership of the things that are being placed in the
    # TObjArary. They get deleted because of result.SetOwner()
    for item in the_list:
        ROOT.SetOwnership(item, False)
        result.Add(item)

    return result


def MultiDraw(self, *draw_list):
    """
    Draws (projects) many histograms in one loop over a tree.

        Instead of:
        tree.Project("hname1", "ph_pt",  "weightA")
        tree.Project("hname2", "met_et", "weightB")

        Do:
        tree.MultiDraw( ("hname1", "ph_pt",  "weightA" ),
                        ("hname2", "met_et", "weightB" ) )
    """

    hnames, variables, selections = [], [], []

    last_variable, last_selection = None, None

    histograms = []
    for i, drawexp in enumerate(draw_list):

        # Expand out origFormula and weight, otherwise just use weight of 1.
        hname, variable, selection = drawexp

        hist = ROOT.gDirectory.Get(hname)
        if not hist:
            raise RuntimeError("MultiDraw: Couldn't find histogram to fill '%s' in current directory." % name)

        histograms.append(hist)

        # The following two 'if' clauses check that the next formula is different
        # to the previous one. If it is not, we add an ordinary TObject.
        # Then, the dynamic cast in MultiDraw.cxx fails, giving 'NULL', and
        # The previous value is used. This saves the recomputing of identical values
        if variable != last_variable:
            f = ROOT.TTreeFormula("variable%i" % i, variable, self)
            if not f.GetTree():
                raise RuntimeError("TTreeFormula didn't compile: %s" % variable)
            f.SetQuickLoad(True)
            variables.append(f)
        else:
            variables.append(ROOT.TObject())

        if selection != last_selection:
            f = ROOT.TTreeFormula("selection%i" % i, selection, self)
            if not f.GetTree():
                raise RuntimeError("TTreeFormula didn't compile: %s" % selection)
            f.SetQuickLoad(True)
            selections.append(f)
        else:
            selections.append(ROOT.TObject())

        last_variable, last_selection = variable, selection


    # Only compile MultiDraw once
    try:
        from ROOT import MultiDraw as _MultiDraw
    except ImportError:
        ROOT.gInterpreter.Declare(multidraw_cxx)
        from ROOT import MultiDraw as _MultiDraw

    # Ensure that formulae are told when tree changes
    fManager = ROOT.TTreeFormulaManager()
    for variable in variables + selections:
        if type(variable) == ROOT.TTreeFormula:
            fManager.Add(variable)

    fManager.Sync()
    self.SetNotify(fManager)

    # Draw everything!
    _MultiDraw(self,
               MakeTObjArray(variables),
               MakeTObjArray(selections),
               MakeTObjArray(histograms),
               len(variables))

    return

ROOT.TTree.MultiDraw = MultiDraw
