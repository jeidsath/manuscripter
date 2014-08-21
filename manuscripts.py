#!/usr/bin/env python
import argparse
import urllib2
import urllib
import re
import os
import requests
import multiprocessing

from PIL import Image


def main():
    desc = 'The www.bl.uk manuscript downloader'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-m', '--manuscript', required=True)
    parser.add_argument('-p', '--page')
    parser.add_argument('--showpages', action='store_true')
    parser.add_argument('--download', action='store_true')

    args = parser.parse_args()
    if args.showpages:
        showpages(args)
    if args.download:
        download(args)


def showpages(args):
    mg = ManuscriptGetter(args.manuscript)
    print(mg.get_pages())


def download(args):
    if args.page:
        mg = ManuscriptGetter(args.manuscript, args.page)
        mg.get_image()
        mg.compose_image()
    else:
        mg = ManuscriptGetter(args.manuscript)
        pages = mg.get_pages()
        for pp in pages:
            if pp == '##':
                continue
            if os.path.exists(os.path.join('data', args.manuscript,
                                           'fullimages', pp + '.jpg')):
                continue

            mg = ManuscriptGetter(args.manuscript, pp)
            mg.get_image()
            mg.compose_image()


def store_subimage(self, xx, yy):
    ManuscriptGetter.store_subimage(self, xx, yy)


class ManuscriptGetter(object):
    def __init__(self, manuscript, page=None):
        self.manuscript = manuscript
        if page:
            self.page = page
            self.mdir = os.path.join('data', self.manuscript)
            self.pdir = os.path.join(self.mdir, self.page)
            self.subdir = os.path.join(self.pdir, 'subimages')
            self.fulldir = os.path.join(self.mdir, 'fullimages')
            try:
                os.makedirs(self.subdir)
            except OSError:
                pass
            try:
                os.makedirs(self.fulldir)
            except OSError:
                pass

    def get_pages(self):
        page_url = 'http://www.bl.uk/manuscripts/Viewer.aspx?ref={manu}'
        real_url = page_url.format(manu=self.manuscript)
        uu = requests.get(real_url)
        lines = uu.text.split('\n')
        for ll in lines:
            if re.match('.*name="PageList" id="PageList".*', ll):
                mm = re.search('value="(.*)"', ll)
                pages = mm.group(1).split('||')
        pages = [pp.replace(self.manuscript + '_', '') for pp in pages]
        return pages

    def get_num_images(self, size):
        if size <= 257:
            return 1
        additional = size - 257
        if additional / 258 * 258 == additional:
            return 1 + additional / 258
        else:
            return 1 + additional / 258 + 1

    def get_sizes(self):
        size_url = ('http://www.bl.uk/manuscripts/Proxy.ashx' +
                    '?view={manu}_{page}.xml')
        real_url = size_url.format(manu=self.manuscript, page=self.page)
        pp = urllib2.urlopen(real_url)
        mm = re.search('Width="(\d+).*Height="(\d+)"', pp.read())
        return int(mm.group(1)), int(mm.group(2))

    def store_subimage(self, xx, yy):
        print("Storing {manuscript} {page} {xx} {yy}".format(
            manuscript=self.manuscript, page=self.page, xx=xx, yy=yy))
        subimage_url = ('http://www.bl.uk/manuscripts/Proxy.ashx?view=' +
                        '{manu}_{page}_files/13/{xx}_{yy}.jpg')
        formatted_url = subimage_url.format(manu=self.manuscript,
                                            page=self.page,
                                            xx=str(xx),
                                            yy=str(yy))
        shortname = str(xx) + '_' + str(yy) + '.jpg'
        filename = os.path.join(self.subdir, shortname)

        if os.path.exists(filename):
            return
        urllib.urlretrieve(formatted_url, filename)

    def get_image(self):
        xx_size, yy_size = self.get_sizes()
        self.xmax = self.get_num_images(xx_size)
        self.ymax = self.get_num_images(yy_size)
        pool = multiprocessing.Pool(processes=4)
        for xx in range(0, self.xmax):
            for yy in range(0, self.ymax):
                # self.store_subimage(xx, yy)
                pool.apply_async(store_subimage, [self, xx, yy])
        pool.close()
        pool.join()

    def compose_image(self):
        print 'Composing image {0} {1}'.format(self.manuscript, self.page)
        outfile = os.path.join(self.fulldir, self.page + '.jpg')
        new_xsize = 257 + (self.xmax - 1) * 258
        new_ysize = 257 + (self.ymax - 1) * 258
        outImage = Image.new('RGB', (new_xsize, new_ysize))
        for xx in range(0, self.xmax):
            for yy in range(0, self.ymax):
                shortname = str(xx) + '_' + str(yy) + '.jpg'
                filename = os.path.join(self.subdir, shortname)
                sub = Image.open(filename)
                xoff = 0
                yoff = 0
                if xx > 0:
                    xoff = 257 + (xx - 1) * 258
                if yy > 0:
                    yoff = 257 + (yy - 1) * 258
                box = (xoff, yoff, xoff + sub.size[0], yoff + sub.size[1])
                outImage.paste(sub, box)
        outImage.save(outfile)

if __name__ == '__main__':
    main()
