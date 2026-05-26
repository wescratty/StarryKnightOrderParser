"""
html.table.header
html.table.row.cell
"""


class Html:
    def __init__(self):
        self.get = self.Get()

    class Maker:
        def __init__(self):
            self.table = Html.Table
            self.ordered_list = Html.OList
            self.u_ordered_list = Html.UOList
            self.descriptive_list = Html.DescriptiveList

    class Tools:
        def __init__(self):
            self.great = '<'
            self.less = '>'
            self.slash = '/'

    class Table:
        def __init__(self):
            # table
            # self.table_style = '<style>table {border-collapse: collapse;th, td {border: 1px solid black;}</style>'
            # self.table_style = '<style> tr:hover {background-color: #D6EEEE;}</style>'
            # self.table_style = '<style>tr {border-bottom: 1px solid #ddd;}</style>'
            self.table_style = '<style>td:nth-child(even), th:nth-child(even) {background-color: #D6EEEE;}, tr: {border: 1px solid #ddd;}</style>'
            # self.table_style = '<style>table, th, td {border: 0.5px solid black;}</style>'
            self.table = 'table'
            self.thead = 'thead'
            self.tbody = 'tbody'
            self.header = 'th'
            self.cell = 'td'
            self.row = 'tr'
            self.op = Html.Op()
            self.tags = Html.Tags()

        def create(self, table_dict):
            print(table_dict)
            ret = self.table_style

            sections = table_dict.keys()
            for section in sections:
                section_title = ''
                header_row = self.op.open(self.thead) + self.op.open(self.row)
                for header in table_dict[section].keys():
                    if table_dict[section][header] == 'Break':
                        section_title += header
                    else:
                        header_row += self.op.open(self.header) + header + self.op.close(self.header)
                header_row += self.op.close(self.row) + self.op.close(self.thead)
                ret += self.op.open(self.tags.h2) + section_title + self.op.close(self.tags.h2)
                ret += self.op.open(self.table) + header_row

                ret += self.op.open(self.tbody)
                ret += self.op.open(self.row)
                for header in table_dict[section].keys():
                    if table_dict[section][header] != 'Break':
                        if table_dict[section][header].startswith('http'):
                            ret += self.op.open(self.cell) + '<a href="' + table_dict[section][header] + '">  Link </a>' + \
                                   self.op.close(self.cell)
                        else:
                            ret += self.op.open(self.cell) + table_dict[section][header] + self.op.close(self.cell)
                ret += self.op.close(self.row)
                ret += self.op.close(self.row)
                ret += self.op.close(self.tbody)
                ret += self.op.close(self.table)
                # print(ret)

            return ret

    class OList:
        def __init__(self):
            # list
            self.list_style = '<style></style>'

            self.ordered_list = 'ol'
            self.li = 'li'
            self.op = Html.Op()
            self.tags = Html.Tags()


        def create(self, table_dict):
            # print("OLIST")
            # print(table_dict)
            ret = self.list_style

            # sections = table_dict.keys()
            # for section in sections:
            #     section_title = ''
            #     header_row = self.op.open(self.thead) + self.op.open(self.row)
            #     for header in table_dict[section].keys():
            #         if table_dict[section][header] == 'Break':
            #             section_title += ' - ' + header
            #         else:
            #             header_row += self.op.open(self.header) + header + self.op.close(self.header)
            #     header_row += self.op.close(self.row) + self.op.close(self.thead)
            #     ret += self.op.open(self.tags.h2) + section_title + self.op.close(self.tags.h2)
            #     ret += self.op.open(self.table) + header_row
            #
            #     ret += self.op.open(self.tbody)
            #     ret += self.op.open(self.row)
            #     for header in table_dict[section].keys():
            #         if table_dict[section][header] != 'Break':
            #             if table_dict[section][header].startswith('http'):
            #                 ret += self.op.open(self.cell) + '<a href="' + table_dict[section][
            #                     header] + '">  Link </a>' + \
            #                        self.op.close(self.cell)
            #             else:
            #                 ret += self.op.open(self.cell) + table_dict[section][header] + self.op.close(self.cell)
            #     ret += self.op.close(self.row)
            #     ret += self.op.close(self.row)
            #     ret += self.op.close(self.tbody)
            #     ret += self.op.close(self.table)
            #     print(ret)
            #
            # return ret

    class UOList:
        def __init__(self):
            # list
            self.u_ordered_list = 'ul'
            self.li = 'li'

        def create(self, items):
            pass

    class DescriptiveList:
        def __init__(self):
            # descriptive list
            self.dl = 'dl'
            self.dt = 'dt'
            self.dd = 'dd'

        def create(self, items):
            pass

    class Tags:
        def __init__(self):
            self.h1 = 'h1'
            self.h2 = 'h2'
            self.h3 = 'h3'
            self.h4 = 'h4'
            self.h5 = 'h5'
            self.h6 = 'h6'
            self.div = 'div'
            self.par = 'p'
            self.html = 'html'
            self.head = 'head'
            self.body = 'body'
            self.br = 'br'
            self.title = 'title'
            self.link = 'link'

    class Get:
        def __init__(self):
            self.make = Html.Maker()
            self.tags = Html.Tags()
            self.op = Html.Op()
            # self.table = Html.Table()

        def table(self, table_dict):
            table = Html.Table()
            ret = self.op.open(self.tags.html)
            ret += self.make.table.create(table, table_dict)
            ret += self.op.close(self.tags.html)
            return ret

        def ordered_list(self, table_dict):
            ol = Html.OList()

            ret = self.op.open(self.tags.html)
            ret += self.make.ordered_list.create(ol, table_dict)
            ret += self.op.close(self.tags.html)
            return ret


        # def u_ordered_list(self, header, list_of_rows):
        #     ret = self.make.u_ordered_list.create()
        #     return ret
        #
        # def descriptive_list(self, header, list_of_rows):
        #     ret = self.make.descriptive_list.create()
        #     return ret

    class Op:
        def __init__(self):
            self.tools = Html.Tools()

        def open(self, tag):
            return self.tools.great + tag + self.tools.less

        def close(self, tag):
            return self.tools.great + self.tools.slash + tag + self.tools.less
