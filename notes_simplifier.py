import cv2
import numpy as np


class Parameters:
    columns = 1
    folder = "mystery of love"
    min_line_size = 50#auto
    max_line_size = 85#auto
    instrument_nr = 4
    line_black_tolerance = 254.53#auto
    line_block_tolerance = 254.74#auto
    how_many_img = 44
    max_lines_in_column = 18#ile linii w pliku wynikowym moze byc pod soba
    padding = 50#auto
    lines_in_block = 6


def line_connector(lines, page_nr, parameters):
    padding = parameters.padding
    first_height = 0
    height = 0
    width = 0
    prev_height = 0

    # create empty image in appropriate size
    line_nr = 0
    for line in lines:
        line_nr += 1
        if line_nr == parameters.max_lines_in_column + 1:
            first_height = height
            height = 0
        if line is not None:
            prev_height = len(line)
            height += prev_height
            if len(line) > width:
                width = len(line[0])
        else:
            print("error: empty line")
            height += prev_height
    if first_height > height:
        height = first_height
    if first_height != 0:
        width *= 2
        width += padding
    img = np.zeros((height + padding*2, width + padding*2, 3), np.uint8)
    img.fill(255)

    # put lines in image
    w1 = padding
    h1 = padding
    prev_height = 0
    line_nr = 0
    for line in lines:
        line_nr += 1
        if line is not None:
            prev_height = len(line)
            w2 = w1 + len(line[0])
            if line_nr == parameters.max_lines_in_column + 1:
                w1 = int((width - padding) / 2 + padding)
                w2 += w1
                h1 = padding
            h2 = h1 + prev_height
            # print("shape", w1, h1)
            img[h1:h2, w1:w2, :3] = line
            h1 = h2
        else:
            h2 = h1 + prev_height
            h1 = h2
    cv2.imshow(str(page_nr), img)
    cv2.imwrite(parameters.folder + str(page_nr) + ".png", img)


# check if a row is black enough to be notes
def row_has_enough_black(row, black_tolerance):
    suma = 0
    for pixel in row:
        suma += sum(pixel) / 3
    avg = suma / len(row)
    if avg < black_tolerance:
        return True
    else:
        return False


# dzieli blok nut na linie i zwraca linie z wyznaczonej linii melodycznej
def line_separator(img, parameters):
    add_line = False
    lines = []
    line = []
    prev_has_black = False
    for row in img:
        row_has_black = False
        if row_has_enough_black(row, parameters.line_black_tolerance):
            row_has_black = True
            add_line = True
        # check each pixel if black
        """
        for pi in range(len(row)):
            pixel = row[pi]
            if is_black_enough(pixel):
                how_many_black += 1
                if how_many_black > 3:
                    row_has_black = True
                    add_line = True
        """
        if not row_has_black:
            add_line = False
            if prev_has_black:  # jeśli poprzedni wiersz miał w sobie czarny
                if len(line) > parameters.min_line_size:
                    lines.append(line)
                line = []
        if add_line:
            line.append(row)
            if len(line) > parameters.max_line_size:
                lines.append(line)
                line = []
        prev_has_black = row_has_black
    i = 0
    if len(lines) != parameters.lines_in_block:
        print("error: detected lines " + str(len(lines)) + "/"+str(parameters.lines_in_block))
    for line in lines:
        i += 1
        shape = [len(line), len(line[0])]
        lineimg = np.zeros((shape[0], shape[1], 3), np.uint8)
        lineimg[:shape[1], :shape[1], :3] = line
        # cv2.imshow("line" + str(i), lineimg)
        if i == parameters.instrument_nr:
            return lineimg


# skraca obraz, usuwając białe piksele po lewej i prawej stronie nut
def remove_white_space(img):
    # sprawdza piksele po obu stronach ekranu. sprawdza 10% pikseli z prawej i lewej
    border_size = int(len(img[0]) * 0.10)
    max_l = 0
    min_r = len(img[0])
    for row in img:
        for border in range(border_size):
            pixel_l = sum(row[border]) / 3
            border_r = len(row) - 1 - border
            pixel_r = sum(row[border_r]) / 3
            # jesli pixel ok. czarny, to jest potencjalną granicą
            if pixel_l < 50:
                if border > max_l:
                    max_l = border
            if pixel_r < 50:
                if border_r < min_r:
                    min_r = border_r

    new_img = np.zeros((len(img), min_r - max_l, 3), np.uint8)
    for i in range(len(img)):
        new_img[i] = img[i, max_l:min_r, :3]
    return new_img


def divide_blocks(img_all, parameters):
    # dziele obraz na 2, gdy ma dwie kolumny
    img_parts = []
    end_of_img = len(img_all[0])
    if parameters.columns == 2:
        img_parts.append(img_all[:-1, :int(end_of_img / 2), :3])
        img_parts.append(img_all[:-1, int(end_of_img / 2):end_of_img, :3])
    if parameters.columns == 1:
        img_parts.append(img_all)

    # znaleziony obszar z czarnym kolorem
    black_area_list = []
    black_area = []
    for img in img_parts:
        for row in img:
            block_tolerance = 1.001 * parameters.line_black_tolerance
            is_notes = row_has_enough_black(row, block_tolerance)
            if is_notes:
                black_area.append(row)
            else:
                if len(black_area) > parameters.min_line_size:
                    black_area_list.append(black_area)
                black_area = []

    img_list = []
    for i in range(len(black_area_list)):
        # wydzielony blok nut
        area = black_area_list[i]
        img = np.zeros((len(area), len(area[0]), 3), np.uint8)
        img[:len(img), :len(img[0]), :3] = area
        # cv2.imshow("black area" + str(i+1), img)
        img_list.append(img)
    return img_list


def scale_img(img, scale_percent):
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv2.resize(img, dim, 3)
    return resized


# DO SPRAWDZENIA: rozdzielanie na kilka stron
def img_reader(parameters):
    directory = parameters.folder
    lines = []
    print(parameters.folder)
    for i in range(parameters.how_many_img):
        filename = directory + "/" + str(i + 1) + ".PNG"
        print("\npage "+str(i+1)+"/"+str(parameters.how_many_img))
        img_all = cv2.imread(filename)
        img_list = divide_blocks(img_all, parameters)
        for j in range(len(img_list)):
            img = img_list[j]
            img = remove_white_space(img)
            # scale to the same size
            # img=scale_img(img,70)
            #cv2.imshow("page " + str(j+1), img)
            img_list[j] = img
            # teraz rodzdielanie linii
            line = line_separator(img, parameters)
            lines.append(line)
            print("added line " + str(len(lines)))
    # oblicznie, ile stron trzeba robic
    if len(lines) > parameters.max_lines_in_column * 2:
        page_nr = 1
        lines_part = []
        for i in range(len(lines)):
            line = lines[i]
            lines_part.append(line)
            if i + 1 == parameters.max_lines_in_column * 2:
                line_connector(lines_part, page_nr, parameters)
                page_nr += 1
                lines_part = []
        line_connector(lines_part, page_nr, parameters)
    else:
        line_connector(lines, 1, parameters)
    key = 0
    while not key == 32:
        key = cv2.waitKey()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    package = '2'  # input("1 = mystery of love, 2 = death with dignity ")
    parameters = Parameters()
    if package == '1':
        parameters.columns = 1
        parameters.folder = "mystery of love"
        parameters.min_line_size = 50
        parameters.max_line_size = 85
        parameters.instrument_nr = 4
        parameters.line_black_tolerance = 254.53
        parameters.line_block_tolerance = 254.74
        parameters.how_many_img = 44
        parameters.max_lines_in_column = 18
        parameters.padding = 50
        parameters.lines_in_block = 6
    if package == '2':
        parameters.columns = 2
        parameters.folder = "death with dignity"
        parameters.min_line_size = 30
        parameters.max_line_size = 50
        parameters.instrument_nr = 1
        parameters.line_black_tolerance = 254.53
        parameters.line_block_tolerance = 254.74
        parameters.how_many_img = 3
        parameters.max_lines_in_column = 18
        parameters.padding = 25
        parameters.lines_in_block = 6
    img_reader(parameters)