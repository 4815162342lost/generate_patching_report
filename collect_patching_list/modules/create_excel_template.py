def create_formats(xls_file):
    # create xslsx-file's template
    format_colors=('format_red', 'format_green', 'format_purple',
                   'format_bold', 'format_border', 'format_kernel', 'format_reboot', 'format_green_url', 'format_red_url', 'format_purple_url')

    format={}
    for current_format in format_colors:
        format[current_format]=xls_file.add_format()
        format[current_format].set_border(1)

    format['format_red'].set_bg_color("#ffa7a7")
    format['format_green'].set_bg_color("#96d67c")
    format['format_purple'].set_bg_color("#d195ec")
    format['format_bold'].set_bold()
    format['format_green_url'].set_bg_color("#96d67c")
    format['format_red_url'].set_bg_color("#ffa7a7")
    format['format_purple_url'].set_bg_color("#d195ec")
    for current_url_format in ('format_green_url', 'format_red_url', 'format_purple_url'):
        format[current_url_format].set_font_color("blue")
        format[current_url_format].set_underline()
    return format


def create_total_sheet(xls_file, format):
    # create total sheet
    total_sheet = xls_file.add_worksheet("Total")
    total_sheet.set_tab_color("yellow")
    total_sheet.write(0, 0, "Summary results:", format['format_bold'])

    # select width for columns
    column_width = (20, 50, 14, 16)
    for idx in range(4):
        total_sheet.set_column(idx, idx, width=column_width[idx])

    comments_for_total_sheet=("Server name", "Cycle results(fully patches or state the issue occurred)", "Kernel update",
                              "Reboot required")

    for idx, current_comment in enumerate(comments_for_total_sheet):
        total_sheet.write(1, idx, current_comment, format['format_bold'])
    return total_sheet


def create_xlsx_legend(total_sheet, format):
    """Add legend to total sheet"""
    total_sheet.write(0, 5, "Conventions and stats:", format['format_bold'])
    total_sheet.set_column(5, 5, width=30)
    total_sheet.set_column(6, 6, width=12)
    total_sheet.write(2, 5, "Patching is not required", format['format_green'])
    total_sheet.write(3, 5, "Server needs patching", format['format_red'])
    total_sheet.write(4, 5, "There are problem with the server", format['format_purple'])
    total_sheet.write(1, 5, "Server count", format['format_bold'])


def add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format):
    """Add chart"""
    chart_before_patching = xls_file.add_chart({'type': 'pie'})
    total_sheet.write_formula(1, 6, '=SUM(G3:G5)', format['format_border'])
    total_sheet.write(3, 6, need_patching, format['format_border'])
    total_sheet.write(2, 6, not_need_patching, format['format_border'])
    total_sheet.write(4, 6, error_count, format['format_border'])
    chart_before_patching.set_title({"name": "Stats"})
    chart_before_patching.add_series({
        'categories': '=Total!$F$3:$F$5',
        'values': '=Total!$G$3:$G$5',
        'points': [
            {'fill': {'color': '#79eca3'}},
            {'fill': {'color': '#FF7373'}},
            {'fill': {'color': '#cb87fb'}},
        ],
    })
    total_sheet.insert_chart('F10', chart_before_patching)

def write_to_total_sheet(content, patching_type, sheet, total_sheet, format, idx_glob, os):
    '''content -- patching count or error type'''
    if patching_type!="error":
        if content == 0:
            sheet.set_tab_color("#79eca3")
            sheet.set_column(0, 0, width=21)
            sheet.write(0, 0, "Update is not required", format['format_bold'])
            total_sheet.write(idx_glob + 2, 1, "All packages are up to date", format['format_green'])
            total_sheet.write_url(row=idx_glob + 2, col=0, url="internal:'{sheet_name}'!A1".format(sheet_name=sheet.get_name()), string=sheet.get_name(), cell_format=format['format_green_url'])
        else:
            sheet.set_tab_color("#FF7373")
            sheet.write(1, 0, 'Package name', format['format_bold'])
            if os!='open_suse':
                sheet.write(1, 1, 'Current version', format['format_bold'])
                sheet.write(1, 2, 'Available version', format['format_bold'])
            if content==1:
                sheet.write(0, 0, "Only one {security}patch is available".format(security=patching_type),
                            format['format_bold'])
            else:
                sheet.write(0, 0, str(content) + " {security}patches are available".format(security=patching_type), format['format_bold'])
            total_sheet.write(idx_glob + 2, 1, str(content) + " {security}patсhes are available".format(security=patching_type),
                              format['format_red'])
            total_sheet.write_url(row=idx_glob + 2, col=0, url="internal:'{sheet_name}'!A1".format(sheet_name=sheet.get_name()), string=sheet.get_name(), cell_format=format['format_red_url'])
    else:
        total_sheet.write(idx_glob + 2, 1, "error: " + str(content), format['format_purple'])
        total_sheet.write_url(row=idx_glob + 2, col=0, url="internal:'{sheet_name}'!A1".format(sheet_name=sheet.get_name()), string=sheet.get_name(), cell_format=format['format_purple_url'])
        total_sheet.write(idx_glob + 2, 3, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 4, "unknown", format['format_purple'])
        sheet.set_tab_color("purple")
        sheet.write(0,0,content, format["format_bold"])
