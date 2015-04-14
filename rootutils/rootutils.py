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

    return hist


def histogram_equal_to(hist):
    newhist = hist.Clone(name)
    newhist.Reset()
    return newhist


def normalize_to(hist, other, xmin=None, xmax=None):
    if xmin and xmax:
        n1 = hist.Integral(hist.FindBin(xmin), hist.FindBin(xmax))
        n2 = other.Integral(other.FindBin(xmin), other.FindBin(xmax))
    else:
        n1 = hist.Integral()
        n2 = other.Integral()
    s = n2/n1 if n1 > 0.0 else 1.0
    hist.Scale(s)
    return s

# def get_cumulative(self, inverse=False):
#         """ get cumulative histogram """

#         hist = Hist.equal_to(self)
#         nx = hist.GetNbinsX()
#         for bx in range(nx):
#             if inverse_x:
#                 cum = self.Integral(1, bx+1)
#             else:
#                 cum = self.Integral(bx+1, nx)

#             hist.SetBinContent(bx+1, cum)
#         return hist

def add_overflow_bin(hist):
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

def scale(hist, c, err_c=None):
    """ Scale histogram by a factor with error (c +- err_c)

    * c could be a Value(), or a number
    * err_c could be a number or None.
    * If error is None and c is not a Value(), it does the same as TH1.Scale()
    """
    try:
        c, err_c = c.mean, c.error
    except AttributeError:
        pass

    if err_c is None:
        hist.Scale(c)
        return

    for b in xrange(self.GetNbinsX()):
        hist.SetBinContent(b+1, hist.GetBinContent(b+1) * c)
        err2 = (hist.GetBinContent(b+1) * err_c)**2 + (c * hist.GetBinError(b+1))**2
        hist.SetBinError(b+1, math.sqrt(err2))




def histogram2d(name, nx=None, xmin=None, xmax=None, ny=None, ymin=None, ymax=None, xbins=None, ybins=None):

    if xbins is not None and ybins is not None:
        hist = ROOT.TH2F(name, name, len(xbins)-1, array('d', xbins), len(ybins)-1, array('d', ybins))
    elif nx is not None and ny is not None:
        hist = ROOT.TH2F(name, name, nx, xmin, xmax, ny, ymin, ymax)
    self.SetDirectory(0)


def normalize_hist(hist):
    area = hist.Integral()
    if area > 0:
        hist.Scale(1/area)

def get_cumulative(hist, inverse_x=False, inverse_y=False):

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

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, item):
        self.data[key] = item

    def __iter__(self):
        return self.data.iteritems()


#-----------
# Style
#-----------
colourdict = {
    'orange':      '#E24A33',
    'purple':      '#7A68A6',
    'blue':        '#348ABD',
    'lblue':       '#68add5',
    'turquoise':   '#188487',
    'red':         '#A60628',
    'pink':        '#CF4457',
    'green':       '#467821',
    'yellow':      '#e2a233',
    'lyellow':     '#f7fab3',
    'grey':        '#838283',
    'gray':        '#838283',
}

def get_color(c):
    if isinstance(c, str):
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

def set_color(obj, color, fill=False, alpha=None):
    color = get_color(color)
    obj.SetLineColor(color)
    obj.SetMarkerColor(color)
    if fill:
        if alpha is not None:
            obj.SetFillColorAlpha(color, alpha)
        else:
            obj.SetFillColor(color)

def set_hist_style(hist, **kwargs):

    color = kwargs.get('color', 'kBlack')
    fill = kwargs.get('fill', False)

    marker_style = kwargs.get('mstyle', 20)
    fill_style = kwargs.get('fstyle', None)
    line_style = kwargs.get('lstyle',None)

    marker_size = kwargs.get('msize', 0.8)
    line_width = kwargs.get('lwidth', 2)

    # default
    hist.SetStats(0)
    hist.SetTitle('')

    # color
    set_color(hist, color, fill)

    # marker
    hist.SetMarkerStyle(marker_style)
    hist.SetMarkerSize(marker_size)

    # line
    hist.SetLineWidth(line_width)
    if line_style is not None:
        hist.SetLineStyle(line_style)

    # fill
    if fill_style is not None:
        hist.SetFillStyle(fill_style)

def set_graph_style(graph, **kwargs):

    color = kwargs.get('color', ROOT.kBlack)
    fill = kwargs.get('fill', False)

    marker_style = kwargs.get('mstyle', 20)
    fill_style = kwargs.get('fstyle', None)
    line_style = kwargs.get('lstyle',None)

    marker_size = kwargs.get('msize', 0.8)
    line_width = kwargs.get('lwidth', 2)

    alpha = kwargs.get('alpha', None)

    # default
    graph.SetTitle('')

    # color
    set_color(graph, color, fill, alpha)

    # marker
    graph.SetMarkerStyle(marker_style)
    graph.SetMarkerSize(marker_size)

    # line
    graph.SetLineWidth(line_width)
    if line_style is not None:
        graph.SetLineStyle(line_style)

    # fill
    if fill_style is not None:
        graph.SetFillStyle(fill_style)

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


#-- Plots --
def  create_canvas(name='', title=None, xsize=None, ysize=None, logy=False):
    if title is None:
        title = name
    c = ROOT.TCanvas(name, title, xsize, ysize)
    ROOT.SetOwnership(c, False)
    c.SetTopMargin(0.04)
    if logy:
        c.SetLogy()
    return c

def create_legend(xmin, xmax, ymin, ymax, columns=1):
    leg = ROOT.TLegend(xmin, ymin, xmax, ymax)
    leg.SetFillColor(0)
    leg.SetBorderSize(0)
    if columns > 1:
        leg.SetNColumns(columns)
    return leg
