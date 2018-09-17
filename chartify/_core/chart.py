# -*- coding: utf-8 -*-
#
# Copyright (c) 2017-2018 Spotify AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""


"""
from collections import OrderedDict
from io import BytesIO
import tempfile
import warnings

import bokeh
import bokeh.plotting
from bokeh.embed import file_html

from bokeh.resources import INLINE
from IPython.display import display
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from chartify._core.style import Style
from chartify._core.axes import BaseAxes
from chartify._core.plot import BasePlot
from chartify._core.callout import Callout
from chartify._core.options import options


class Chart:
    """Class Docstring

    - Styling (.style)
    - Plotting (.plot)
    - Callouts (.callout)
    - Axes (.axes)
    - Bokeh figure (.figure)

    """

    def __init__(self,
                 blank_labels=options.get_option('chart.blank_labels'),
                 layout='slide_100%',
                 x_axis_type='linear',
                 y_axis_type='linear'):
        """Create a chart instance.

        Args:
            blank_labels (bool): When true removes the title,
                subtitle, axes, and source labels from the chart.
                Default False.
            layout (str): Change size & aspect ratio of the chart for
                fitting into slides.
                - 'slide_100%'
                - 'slide_75%'
                - 'slide_50%'
                - 'slide_25%'
            x_axis_type (enum, str): Type of data plotted on the X-axis.
                - 'linear':
                - 'log':
                - 'datetime': Use for datetime formatted data.
                - 'categorical':
                - 'density'

            y_axis_type (enum, str): Type of data plotted on the Y-axis.
                - 'linear':
                - 'log':
                - 'categorical':
                - 'density'
        Note:
            Combination of x_axis_type and y_axis_type will determine the
            plotting methods available.
        """
        # Validate axis type input
        valid_x_axis_types = [
            'linear', 'log', 'datetime', 'categorical', 'density'
        ]
        valid_y_axis_types = ['linear', 'log', 'categorical', 'density']
        if x_axis_type not in valid_x_axis_types:
            raise ValueError('x_axis_type must be one of {options}'.format(
                options=valid_x_axis_types))
        if y_axis_type not in valid_y_axis_types:
            raise ValueError('y_axis_type must be one of {options}'.format(
                options=valid_y_axis_types))

        self._x_axis_type, self._y_axis_type = x_axis_type, y_axis_type

        self._blank_labels = options._get_value(blank_labels)
        self.style = Style(self, layout)
        self.figure = self._initialize_figure(self._x_axis_type,
                                              self._y_axis_type)
        self.style._apply_settings('chart')
        self.plot = BasePlot._get_plot_class(self._x_axis_type,
                                             self._y_axis_type)(self)
        self.callout = Callout(self)
        self.axes = BaseAxes._get_axis_class(self._x_axis_type,
                                             self._y_axis_type)(self)
        self._source = self._add_source_to_figure()
        self._subtitle_glyph = self._add_subtitle_to_figure()
        self.figure.toolbar.logo = None  # Remove bokeh logo from toolbar.
        # Logos disabled for now.
        # self.logo = Logo(self)
        # Set default for title
        title = """ch.set_title('Takeaway')"""
        if self._blank_labels:
            title = ""
        self.set_title(title)

    def __repr__(self):
        return """
chartify.Chart(blank_labels={blank_labels},
layout='{layout}',
x_axis_type='{x_axis_type}',
y_axis_type='{y_axis_type}')
""".format(blank_labels=self._blank_labels,
           layout=self.style._layout,
           x_axis_type=self._x_axis_type,
           y_axis_type=self._y_axis_type)

    def _initialize_figure(self, x_axis_type, y_axis_type):
        x_range, y_range = None, None
        if x_axis_type == 'categorical':
            x_range = []
            x_axis_type = 'auto'
        if y_axis_type == 'categorical':
            y_range = []
            y_axis_type = 'auto'
        if x_axis_type == 'density':
            x_axis_type = 'linear'
        if y_axis_type == 'density':
            y_axis_type = 'linear'
        figure = bokeh.plotting.figure(
            x_range=x_range,
            y_range=y_range,
            y_axis_type=y_axis_type,
            x_axis_type=x_axis_type,
            plot_width=self.style.plot_width,
            plot_height=self.style.plot_height,
            tools='save',
            # toolbar_location='right',
            active_drag=None)
        return figure

    def _add_subtitle_to_figure(self, subtitle_text=None):
        """Create the subtitle glyph and add it to the bokeh figure."""
        if subtitle_text is None:
            subtitle_text = """ch.set_subtitle('Data Description')"""
        if self._blank_labels:
            subtitle_text = ""
        subtitle_settings = self.style._get_settings('subtitle')
        _subtitle_glyph = bokeh.models.Title(
            text=subtitle_text,
            align=subtitle_settings['subtitle_align'],
            text_color=subtitle_settings['subtitle_text_color'],
            text_font_size=subtitle_settings['subtitle_text_size'],
            text_font=subtitle_settings['subtitle_text_font'])
        self.figure.add_layout(_subtitle_glyph,
                               subtitle_settings['subtitle_location'])
        return _subtitle_glyph

    def _add_source_to_figure(self):
        """Create the source glyph and add it to the bokeh figure."""
        source_text = """ch.set_source_label('Source')"""
        if self._blank_labels:
            source_text = ""
        source_text_color = '#898989'
        source_font_size = '10px'
        _source = bokeh.models.Label(
            x=self.style.plot_width * .9,
            y=-55,
            x_units='screen',
            y_units='screen',
            level='overlay',
            text=source_text,
            text_color=source_text_color,
            text_font_size=source_font_size,
            text_align='right',
            name='subtitle')
        self.figure.add_layout(_source)
        return _source

    @property
    def data(self):
        """Return a list of dictionaries of the data that have be plotted on the chart.

        Note:
            The format will depend on the types of plots that have been added.
        """
        datasources = self.figure.select({
            'type': bokeh.models.ColumnDataSource
        })
        # Extract the data attribute from the ColumnDataSource object
        # and place in a list.
        datasources_list = list(map(lambda x: x.data, datasources))
        return datasources_list

    @property
    def source_text(self):
        """str: Data source of the chart."""
        return self._source.text

    def set_source_label(self, source):
        """Set the chart data source.

        Args:
            source (str): Data source.

        Returns:
            Current chart object
        """
        self._source.text = source
        return self

    @property
    def title(self):
        """str: Title text of the chart."""
        return self.figure.title.text

    def set_title(self, title):
        """Set the chart title.

        Args:
            title (str): Title text.

        Returns:
            Current chart object
        """
        self.figure.title.text = title
        return self

    @property
    def subtitle(self):
        """str: Subtitle text of the chart."""
        return self._subtitle_glyph.text

    def set_subtitle(self, subtitle):
        """Set the chart subtitle.

        Args:
            subtitle (str): Subtitle text.

        Note:
            Set value to "" to remove subtitle.

        Returns:
            Current chart object
        """
        self._subtitle_glyph.text = subtitle
        return self

    @property
    def legend_location(self):
        """str: Legend location."""
        return self.figure.legend[0].location

    def set_legend_location(self, location, orientation='horizontal'):
        """Set the legend location.

        Args:
            location (str or tuple): Legend location. One of:
            - Outside of the chart: 'outside_top', 'outside_bottom',
                  'outside_right'
            - Within the chart area: 'top_left', 'top_center',
                  'top_right', 'center_left', 'center', 'center_right',
                  'bottom_left', 'bottom_center', 'bottom_right'
            - Coordinates: Tuple(Float, Float)
            - None: Removes the legend.
            orientation (str): 'horizontal' or 'vertical'

        Returns:
            Current chart object
        """

        def add_outside_legend(legend_location, layout_location):
            self.figure.legend.location = legend_location
            if not self.figure.legend:
                warnings.warn(
                    """
                    Legend location will not apply.
                    Set the legend after plotting data.
                    """, UserWarning)
                return self
            new_legend = self.figure.legend[0]
            new_legend.plot = None
            new_legend.orientation = orientation
            self.figure.add_layout(new_legend, layout_location)

        if location == 'outside_top':
            add_outside_legend('top_left', 'above')
            # Re-render the subtitle so that it appears over the legend.
            subtitle_index = self.figure.renderers.index(self._subtitle_glyph)
            self.figure.renderers.pop(subtitle_index)
            self._subtitle_glyph = self._add_subtitle_to_figure(
                self._subtitle_glyph.text)
        elif location == 'outside_bottom':
            add_outside_legend('bottom_center', 'below')
        elif location == 'outside_right':
            add_outside_legend('top_left', 'right')
        elif location is None:
            self.figure.legend.visible = False
        else:
            self.figure.legend.location = location
            self.figure.legend.orientation = orientation
        return self

    def show(self, format='html'):
        """Show the chart.

        Args:
            format (str):
                - 'html': Output chart as HTML.
                    Renders faster and allows for interactivity.
                    Charts saved as HTML in a Jupyter notebooks
                    WILL NOT display on Github.
                    Logos will not display on HTML charts.
                    Recommended when drafting plots.

                - 'png': Output chart as PNG.
                    Easy to copy+paste into slides.
                    Will render logos.
                    Recommended when the plot is in a finished state.
                """
        self._set_toolbar_for_format(format)

        if format == 'html':
            return bokeh.io.show(self.figure)
        elif format == 'png':
            image = self._figure_to_png()
            # Need to re-enable this when logos are added back.
            # image = self.logo._add_logo_to_image(image)
            return display(image)

    def save(self, filename, format='html'):
        """Save the chart.

        Args:
            filename (str): Name of output file.
            format (str):
                - 'html': Output chart as HTML.
                    Renders faster and allows for interactivity.
                    Charts saved as HTML in a Jupyter notebook WILL NOT display
                    on Github.
                    Logos will not display on HTML charts.
                    Recommended when drafting plots.

                - 'png': Output chart as PNG.
                    Easy to paste into google slides.
                    Recommended when the plot is in a finished state.
                    Will render logos.
        """
        self._set_toolbar_for_format(format)

        if format == 'html':
            bokeh.io.saving.save(
                self.figure,
                filename=filename,
                resources=INLINE,
                title='Chartify chart.')
        elif format == 'png':
            image = self._figure_to_png()
            # Need to re-enable this when logos are added back.
            # image = self.logo._add_logo_to_image(image)
            image.save(filename)

        print('Saved to {filename}'.format(filename=filename))

        return self

    def _set_toolbar_for_format(self, format):
        if format == 'html':
            self.figure.toolbar_location = 'right'
        elif format == 'png':
            self.figure.toolbar_location = None
        elif format is None:  # If format is None the chart won't be shown.
            pass
        else:
            raise ValueError(
                """Invalid format. Valid options are 'html' or 'png'.""")

    def _figure_to_png(self):
        """Convert figure object to PNG
        Bokeh can only save figure objects as html.
        To convert to PNG the HTML file is opened in a headless browser.
        """
        # Initialize headless browser options
        options = Options()
        options.add_argument("window-size={width},{height}".format(
            width=self.style.plot_width, height=self.style.plot_height))
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("disable-gpu")
        options.add_argument('no-sandbox')  # Required for use in docker.
        options.add_argument("--disable-extensions")
        options.add_argument('--headless')
        options.add_argument('--hide-scrollbars')
        driver = webdriver.Chrome(options=options)
        # Save figure as HTML
        html = file_html(self.figure, resources=INLINE, title="")
        fp = tempfile.NamedTemporaryFile(
            'w', prefix='chartify', suffix='.html', encoding='utf-8')
        fp.write(html)
        fp.flush()
        # Open html file in the browser.
        driver.get("file:///" + fp.name)
        driver.execute_script("document.body.style.margin = '0px';")
        png = driver.get_screenshot_as_png()
        driver.quit()
        fp.close()
        # Resize image if necessary.
        image = Image.open(BytesIO(png))
        target_dimensions = (self.style.plot_width, self.style.plot_height)
        if image.size != target_dimensions:
            image = image.resize(target_dimensions, resample=Image.LANCZOS)
        return image


class Logo:

    def __init__(self, chart):
        self._chart = chart
        self._logo_image = None
        self._path = options.get_option('config.logos_path')
        self._logo_file_mapping = {}
        self._logo_file_mapping = OrderedDict(
            sorted(list(self._logo_file_mapping.items()), key=lambda t: t[0]))

    def _add_logo_to_image(self, image):
        """If the logo is set then add it to the chart image."""
        if self._logo_image is None:
            return image

        x_dim = image.getbbox()[2]
        width = self._logo_image.getbbox()[2]
        padding = 10
        coords = (x_dim - width - padding, 0 + padding)
        image.paste(self._logo_image, coords, self._logo_image)
        return image

    def _resize_logo(self, logo_image):

        logo_width, logo_height = logo_image.size

        # TODO smart scaling of logos
        target_height = int(self._chart.style.plot_height * .1)

        if logo_width == logo_height:
            logo_image = logo_image.resize(
                (target_height, target_height), resample=Image.LANCZOS)
        else:
            logo_width_to_height = logo_width * 1.0 / logo_height
            logo_image = logo_image.resize(
                (int(logo_width_to_height * target_height), target_height),
                resample=Image.LANCZOS)
        return logo_image

    def show_logo_options(self):
        for name, filename in self._logo_file_mapping.items():
            logo_image = Image.open(self._path + filename)
            display(name)
            display(self._resize_logo(logo_image))

    def set_logo(self, logo=None):
        """Add logo to the chart.

        Notes:
            Use .show_logo_options() to see available logos.
            Logo will only appear when .show('png') is used.
        """
        try:
            filename = self._logo_file_mapping[logo]
        except KeyError:
            raise KeyError(
                'Must supply a valid logo name: {valid_options}'.format(
                    valid_options=list(self._logo_file_mapping.keys())))

        logo_image = Image.open(self._path + filename)

        logo_image = self._resize_logo(logo_image)

        self._logo_image = logo_image