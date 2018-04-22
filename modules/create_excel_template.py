def create_formats(xls_file):
    # create xslsx-file's template
    format_colors=('format_red', 'format_green', 'format_purple', 'format_yellow', 'format_gray',
                   'format_blue', 'format_bold', 'format_border', 'format_kernel', 'format_reboot',
                    'format_potential_risky_packages')

    format={}
    for current_format in format_colors:
        format[current_format]=xls_file.add_format()
        format[current_format].set_border(1)

    format['format_red'].set_bg_color("#ffa7a7")
    format['format_green'].set_bg_color("#96d67c")
    format['format_purple'].set_bg_color("#d195ec")
    format['format_yellow'].set_bg_color("#fff620")
    format['format_gray'].set_bg_color("#a3a3a3")
    format['format_blue'].set_bg_color("#87cad8")
    format['format_bold'].set_bold()
    format['format_potential_risky_packages'] = xls_file.add_format()
    return format


def create_total_sheet(xls_file, format):
    # create total sheet
    total_sheet = xls_file.add_worksheet("Total")
    total_sheet.set_tab_color("yellow")
    total_sheet.write(0, 0, "Summary results:", format['format_bold'])

    # select width for columns
    column_width = (20, 45, 51, 14, 16, 34)
    for idx in range(0, 6):
        total_sheet.set_column(idx, idx, width=column_width[idx])

    comments_for_total_sheet=("Server name", "Conclusion", "Cycle results(fully patches or state the issue occurred)", "Kernel update",
                              "Reboot required", "All potential risky updates excluded")

    for idx, current_comment in enumerate(comments_for_total_sheet):
        total_sheet.write(1, idx, current_comment, format['format_bold'])
    return total_sheet



def create_xlsx_legend(total_sheet, format):
    """Add legend to total sheet"""
    total_sheet.write(0, 7, "Conventions and stats:", format['format_bold'])
    total_sheet.set_column(7, 7, width=30)
    total_sheet.set_column(8, 8, width=12)
    total_sheet.write(2, 7, "Patching is not required", format['format_green'])
    total_sheet.write(3, 7, "Server needs patching", format['format_red'])
    total_sheet.write(4, 7, "There are problem with the server", format['format_purple'])
    total_sheet.write(5, 7, "Updates installed successfully", format['format_yellow'])
    total_sheet.write(6, 7, "Updates failed", format['format_gray'])
    total_sheet.write(7, 7, "Excluded from patching", format['format_blue'])
    total_sheet.write(1, 7, "Server count", format['format_bold'])


def add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format):
    """Add chart"""
    chart_before_patching = xls_file.add_chart({'type': 'pie'})
    total_sheet.write(3, 8, need_patching, format['format_border'])
    total_sheet.write(2, 8, not_need_patching, format['format_border'])
    total_sheet.write(4, 8, error_count, format['format_border'])
    total_sheet.write(5, 8, "n/a", format['format_border'])
    total_sheet.write_formula(6, 8, "=SUM(I3:I5)-(I6+I8)", format['format_border'])
    total_sheet.write(7, 8, "n/a", format['format_border'])

    chart_before_patching.set_title({"name": "The raw statistic (before patching)"})
    chart_before_patching.add_series({
        'categories': '=Total!$H$3:$H$5',
        'values': '=Total!$I$3:$I$5',
        'points': [
            {'fill': {'color': '#79eca3'}},
            {'fill': {'color': '#FF7373'}},
            {'fill': {'color': '#cb87fb'}},
        ],
    })
    total_sheet.insert_chart('H10', chart_before_patching)

    chart_after_patching = xls_file.add_chart({"type": "pie"})
    chart_after_patching.set_title({"name": "Patching results"})
    chart_after_patching.add_series({
        'categories': '=Total!$H$6:$H$8',
        'values': '=Total!$I$6:$I$8',
        'points': [
            {'fill': {'color': "#fff620"}},
            {'fill': {'color': "#a3a3a3"}},
            {'fill': {'color': "#87cad8"}},
        ],
    })
    total_sheet.insert_chart('H28', chart_after_patching)

def write_to_total_sheet(content, patching_type, sheet, total_sheet, format, idx_glob):
    '''content -- patching count or error type'''
    if patching_type!="error":
        if content == 0:
            sheet.set_tab_color("#79eca3")
            sheet.write(0, 0, "{security}patches are not required".format(security=patching_type), format['format_bold'])
            total_sheet.write(idx_glob + 2, 1, "All security packages are up to date", format['format_green'])
            total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_green'])
        elif content == 1:
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, str(content) + " {security}patch is available".format(security=patching_type), format['format_bold'])
            sheet.write(1, 0, 'Package name', format['format_bold'])
            sheet.write(1, 1, 'Current version', format['format_bold'])
            sheet.write(1, 2, 'Available version', format['format_bold'])
            total_sheet.write(idx_glob + 2, 1, "Only 1 {security}patch is available".format(security=patching_type), format['format_red'])
            total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_red'])
        else:
            sheet.set_tab_color("#FF7373")
            sheet.write(1, 0, 'Package name', format['format_bold'])
            sheet.write(1, 1, 'Current version', format['format_bold'])
            sheet.write(1, 2, 'Available version', format['format_bold'])
            sheet.write(0, 0, str(content) + " {security}patches are available".format(security=patching_type), format['format_bold'])
            total_sheet.write(idx_glob + 2, 1, str(content) + " {security}patсhes are available".format(security=patching_type),
                              format['format_red'])
            total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_red'])
    else:
        total_sheet.write(idx_glob + 2, 1, "error: " + str(content), format['format_purple'])
        total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_purple'])
        total_sheet.write(idx_glob + 2, 3, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 4, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 5, "unknown", format['format_purple'])
