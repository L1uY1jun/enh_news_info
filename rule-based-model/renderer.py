from PIL import Image, ImageDraw, ImageFont
from layout import *
from sample_producer import *
from util import *

def render_rule_based_infographic(data):
    infographic_img = Image.new('RGB', (RuleBasedLayoutRules.PAGE_WIDTH.value, RuleBasedLayoutRules.PAGE_HEIGHT.value), color='#FFFFFF')

    if "image" in data:
        section1, h1 = generate_section1_with_image(data["title"], data["excerpt"], data["image"])
    else:
        section1, h1 = generate_section1_simple(data["title"], data["excerpt"])
    section2, h2 = generate_section2(data["graph"])
    section3, h3 = generate_section3(data["related_facts"])

    available_height = RuleBasedLayoutRules.PAGE_HEIGHT.value - RuleBasedLayoutRules.MARGIN_Y.value * 2
    total_section_height = h1 + h2 + h3
    if total_section_height > available_height:
        adjusted_section2_h = available_height - h1 - h3

        if adjusted_section2_h < S2LayoutRules.GRAPH_MIN_HEIGHT.value:
            adjusted_section2_h = S2LayoutRules.GRAPH_MIN_HEIGHT.value
            adjusted_section3_h = available_height - h1 - adjusted_section2_h
            section3, h3 = generate_section3(data["related_facts"], adjusted_section3_h)

        section2, h2 = generate_section2(data["graph"], adjusted_section2_h)
    
    padding = (available_height - h1 - h2 - h3) // 3
    offset_x = RuleBasedLayoutRules.MARGIN_X.value
    offset_y = RuleBasedLayoutRules.MARGIN_Y.value + padding // 2
    infographic_img.paste(section1, (offset_x, offset_y))

    offset_y += h1 + padding
    infographic_img.paste(section2, (offset_x, offset_y))

    offset_y += h2 + padding
    infographic_img.paste(section3, (offset_x, offset_y))
    
    return infographic_img

def generate_section1_simple(title, excerpt, background_color='#A8D8E4'):
    # Title
    title_img, title_h, title_w = draw_optimal_text(
        text=title,
        max_font=S1LayoutRules.TITLE_FONT_SIZE_MAX.value,
        min_font=S1LayoutRules.TITLE_FONT_SIZE_MIN.value,
        max_height=S1LayoutRules.TITLE_MAX_HEIGHT.value,
        max_width=S1LayoutRules.TITLE_MAX_WIDTH.value,
        limited_text_wrap=True,
        background_color=background_color
    )
    bounding_height = max(S1LayoutRules.TITLE_MIN_HEIGHT.value, title_h)
    centered_title_img = align_img_center(
        img=title_img,
        bounding_height=bounding_height,
        bounding_width=S1LayoutRules.TITLE_MAX_WIDTH.value,
        background_color=background_color
    )
    # Excerpt
    excerpt_img, excerpt_h, excerpt_w = draw_optimal_text(
        text=excerpt,
        max_font=S1LayoutRules.EXCERPT_FONT_SIZE_MAX.value,
        min_font=S1LayoutRules.EXCERPT_FONT_SIZE_MIN.value,
        max_height=S1LayoutRules.EXCERPT_MAX_HEIGHT.value,
        max_width=S1LayoutRules.EXCERPT_MAX_WIDTH.value,
        background_color=background_color
    )
    bounding_height = max(S1LayoutRules.EXCERPT_MIN_HEIGHT.value, excerpt_h)
    centered_excerpt_img= align_img_center(
        img=excerpt_img,
        bounding_height=bounding_height,
        bounding_width=S1LayoutRules.EXCERPT_MAX_WIDTH.value,
        background_color=background_color
    )
    centered_title_w, centered_title_h = centered_title_img.size
    centered_excerpt_w, centered_excerpt_h = centered_excerpt_img.size

    section_width = S1LayoutRules.WIDTH.value
    section_height = centered_title_h + centered_excerpt_h + S1LayoutRules.PAD_Y.value * 3
    
    section1_img = Image.new('RGB', (section_width, section_height), color=background_color)
    offset_x = S1LayoutRules.PAD_X.value
    offset_y = S1LayoutRules.PAD_Y.value
    section1_img.paste(centered_title_img, (offset_x, offset_y))
    
    offset_y += (centered_title_h + S1LayoutRules.PAD_Y.value)
    section1_img.paste(centered_excerpt_img, (offset_x, offset_y))
    # Testing-----------------------------------------------
    # section1_img.show()
    # ------------------------------------------------------
    return section1_img, section_height

def generate_section1_with_image(title, excerpt, image, background_color='#A8D8E4', swap_side=False):
    img_width, img_height = image.size

    image_ratio = img_width / img_height
    if image_ratio <= S1LayoutRules.IMAGE_RATIO_THRESHOLD.value:
        title_img, excerpt_img, img, w = arrange_layout_section1_lr(title, excerpt, image, image_ratio, background_color)

        _, new_img_h = img.size
        _, new_title_h = title_img.size
        _, new_excerpt_h = excerpt_img.size
        section_width = S1LayoutRules.WIDTH.value
        section_height = new_img_h + S1LayoutRules.PAD_Y.value * 2

        section1_img = Image.new('RGB', (section_width, section_height), color=background_color)
        padding = (section_height - new_title_h - new_excerpt_h) // 3
        offset_x = (S1LayoutRules.WIDTH.value - S1LayoutRules.PAD_X.value - w) if swap_side else S1LayoutRules.PAD_X.value
        offset_y = padding
        section1_img.paste(title_img, (offset_x, offset_y))
        
        offset_y += (new_title_h + padding)
        section1_img.paste(excerpt_img, (offset_x, offset_y))
        
        offset_x = 0 if swap_side else S1LayoutRules.PAD_X.value + w
        offset_y = S1LayoutRules.PAD_Y.value
        section1_img.paste(img, (offset_x, offset_y))
    else:
        title_img, excerpt_img, img, w = arrange_layout_section1_hybrid(title, excerpt, image, image_ratio, background_color)

        _, new_img_h = img.size
        _, new_title_h = title_img.size
        _, new_excerpt_h = excerpt_img.size
        section_width = S1LayoutRules.WIDTH.value
        section_height = new_img_h + new_title_h + S1LayoutRules.PAD_Y.value * 3

        section1_img = Image.new('RGB', (section_width, section_height), color=background_color)
        offset_x = S1LayoutRules.PAD_X.value
        offset_y = S1LayoutRules.PAD_Y.value
        section1_img.paste(title_img, (offset_x, offset_y))
        
        excerpt_padding = (section_height - new_title_h - new_excerpt_h) // 2
        offset_x = (S1LayoutRules.WIDTH.value - S1LayoutRules.PAD_X.value - w) if swap_side else S1LayoutRules.PAD_X.value
        offset_y += (new_title_h + excerpt_padding)
        section1_img.paste(excerpt_img, (offset_x, offset_y))
        
        offset_x = 0 if swap_side else S1LayoutRules.PAD_X.value + w
        offset_y += (S1LayoutRules.PAD_Y.value - excerpt_padding)
        section1_img.paste(img, (offset_x, offset_y))

    # Testing-----------------------------------------------
    # section1_img.show()
    # ------------------------------------------------------
    return section1_img, section_height

def arrange_layout_section1_lr(title, excerpt, image, image_ratio, background_color):
    img_width, img_height = image.size
    min_left_width = S1LayoutRules.TITLE_MIN_WIDTH.value
    max_left_width = S1LayoutRules.WIDTH.value - S1LayoutRules.IMAGE_MIN_WIDTH.value - S1LayoutRules.PAD_X.value * 2
    optim_left_width = None
    optim_title_img = None
    optim_excerpt_img = None
    optim_img = None

    for left_width in range(min_left_width, max_left_width, 10):
        title_img, title_h, title_w = draw_optimal_text(
            text=title,
            max_font=S1LayoutRules.TITLE_FONT_SIZE_MAX.value,
            min_font=S1LayoutRules.TITLE_FONT_SIZE_MIN.value,
            max_height=S1LayoutRules.TITLE_MAX_HEIGHT.value,
            max_width=left_width,
            limited_text_wrap=True,
            background_color=background_color
        )
        if title_img == None:
            continue
        
        excerpt_img, excerpt_h, excerpt_w = draw_optimal_text(
            text=excerpt,
            max_font=S1LayoutRules.EXCERPT_FONT_SIZE_MAX.value,
            min_font=S1LayoutRules.EXCERPT_FONT_SIZE_MIN.value,
            max_height=S1LayoutRules.EXCERPT_MAX_HEIGHT.value,
            max_width=left_width,
            limited_text_wrap=True,
            background_color=background_color
        )
        if excerpt_img == None:
            continue
        
        rem_width = S1LayoutRules.WIDTH.value - max(title_w, excerpt_w) - S1LayoutRules.PAD_X.value * 3
        rem_height = S1LayoutRules.IMAGE_MAX_HEIGHT.value
        fitted_img = resize_image(image, rem_width, rem_height)
        fitted_w, fitted_h = fitted_img.size
        adjusted_left_width = S1LayoutRules.WIDTH.value - fitted_w - S1LayoutRules.PAD_X.value * 3

        coverage = (fitted_w * fitted_h) / (rem_width * rem_height)
        if coverage >= S1LayoutRules.IMAGE_COVERAGE_THRESHOLD.value:
            optim_title_img, _, adjusted_title_w = draw_optimal_text(
                text=title,
                max_font=S1LayoutRules.TITLE_FONT_SIZE_MAX.value,
                min_font=S1LayoutRules.TITLE_FONT_SIZE_MIN.value,
                max_height=S1LayoutRules.TITLE_MAX_HEIGHT.value,
                max_width=adjusted_left_width,
                limited_text_wrap=True,
                background_color=background_color
            )
            optim_excerpt_img, _, adjusted_excerpt_w = draw_optimal_text(
                text=excerpt,
                max_font=S1LayoutRules.EXCERPT_FONT_SIZE_MAX.value,
                min_font=S1LayoutRules.EXCERPT_FONT_SIZE_MIN.value,
                max_height=S1LayoutRules.EXCERPT_MAX_HEIGHT.value,
                max_width=adjusted_left_width,
                limited_text_wrap=True,
                background_color=background_color
            )
            optim_left_width = max(adjusted_title_w, adjusted_excerpt_w)
            adjusted_img_height = max(fitted_h, title_h + excerpt_h + S1LayoutRules.PAD_Y.value)
            optim_img = align_img_center(
                img=fitted_img, 
                bounding_height=adjusted_img_height, 
                bounding_width=fitted_w + S1LayoutRules.PAD_X.value * 2, 
                background_color=background_color
            )
            # print(coverage * 100, "%")
            break
    return optim_title_img, optim_excerpt_img, optim_img, optim_left_width

def arrange_layout_section1_hybrid(title, excerpt, image, image_ratio, background_color):
    img_width, img_height = image.size
    min_left_width = S1LayoutRules.EXCERPT_MIN_WIDTH.value
    max_left_width = S1LayoutRules.WIDTH.value - S1LayoutRules.IMAGE_MIN_WIDTH.value - S1LayoutRules.PAD_X.value * 2
    optim_left_width = None
    optim_excerpt_img = None
    optim_img = None

    title_img, title_h, _ = draw_optimal_text(
        text=title,
        max_font=S1LayoutRules.TITLE_FONT_SIZE_MAX.value,
        min_font=S1LayoutRules.TITLE_FONT_SIZE_MIN.value,
        max_height=S1LayoutRules.TITLE_MAX_HEIGHT.value,
        max_width=S1LayoutRules.TITLE_MAX_WIDTH.value,
        limited_text_wrap=True,
        background_color=background_color
    )
    centered_title_img= align_img_center(
        img=title_img,
        bounding_height=title_h,
        bounding_width=S1LayoutRules.TITLE_MAX_WIDTH.value,
        background_color=background_color
    )

    for left_width in range(min_left_width, max_left_width, 10):
        excerpt_img, excerpt_h, excerpt_w = draw_optimal_text(
            text=excerpt,
            max_font=S1LayoutRules.EXCERPT_FONT_SIZE_MAX.value,
            min_font=S1LayoutRules.EXCERPT_FONT_SIZE_MIN.value,
            max_height=S1LayoutRules.EXCERPT_MAX_HEIGHT.value,
            max_width=left_width,
            limited_text_wrap=True,
            background_color=background_color
        )
        if excerpt_img == None:
            continue
        
        rem_width = S1LayoutRules.WIDTH.value - excerpt_w - S1LayoutRules.PAD_X.value * 3
        rem_height = S1LayoutRules.IMAGE_MAX_HEIGHT.value - title_h - S1LayoutRules.PAD_Y.value
        fitted_img = resize_image(image, rem_width, rem_height)
        fitted_w, fitted_h = fitted_img.size
        adjusted_left_width = S1LayoutRules.WIDTH.value - fitted_w - S1LayoutRules.PAD_X.value * 3

        coverage = (fitted_w * fitted_h) / (rem_width * rem_height)
        if coverage >= S1LayoutRules.IMAGE_COVERAGE_THRESHOLD.value:
            optim_excerpt_img, _, adjusted_excerpt_w = draw_optimal_text(
                text=excerpt,
                max_font=S1LayoutRules.EXCERPT_FONT_SIZE_MAX.value,
                min_font=S1LayoutRules.EXCERPT_FONT_SIZE_MIN.value,
                max_height=S1LayoutRules.EXCERPT_MAX_HEIGHT.value,
                max_width=adjusted_left_width,
                limited_text_wrap=True,
                background_color=background_color
            )
            optim_left_width = adjusted_excerpt_w
            adjusted_img_height = max(fitted_h, excerpt_h)
            optim_img = align_img_center(
                img=fitted_img, 
                bounding_height=adjusted_img_height, 
                bounding_width=fitted_w + S1LayoutRules.PAD_X.value * 2, 
                background_color=background_color
            )
            break
    return centered_title_img, optim_excerpt_img, optim_img, optim_left_width

def generate_section2(graph_data, section_height=S2LayoutRules.GRAPH_MAX_HEIGHT.value, background_color='#F8E6D2'):
    graph_img = draw_graph(graph_data)

    graph_max_height = section_height - S2LayoutRules.PAD_Y.value * 2
    graph_max_width = S2LayoutRules.GRAPH_MAX_WIDTH.value
    graph_img = resize_image(graph_img, graph_max_width, graph_max_height)

    section2_img = align_img_center(
        img=graph_img,
        bounding_height=section_height,
        bounding_width=S2LayoutRules.WIDTH.value,
        background_color=background_color
    )
    # Testing---------------------------------------------------
    # section2_img.show()
    # ----------------------------------------------------------
    return section2_img, section_height

def generate_section3(related_facts, max_height=S3LayoutRules.MAX_HEIGHT.value, background_color='#F9E79F'):
    img_dimens = []
    bullet_points = [f'* {fact}' for fact in related_facts]
    section_width = S3LayoutRules.WIDTH.value
    section_height = S3LayoutRules.PAD_Y.value * 2
    total_content_height = 0
    
    for point in bullet_points:
        content_img, content_height, _ = draw_optimal_text(
            text=point,
            max_font=S3LayoutRules.CONTENT_FONT_SIZE.value,
            min_font=S3LayoutRules.CONTENT_FONT_SIZE.value,
            max_height=S3LayoutRules.CONTENT_MAX_HEIGHT.value,
            max_width=S3LayoutRules.CONTENT_WIDTH.value,
            background_color=background_color
        )
        new_height = section_height + content_height + S3LayoutRules.CONTENT_PADDING.value
        if new_height > max_height:
            break
        total_content_height += content_height
        section_height = new_height
        img_dimens.append((content_img, content_height))
    
    section3_img = Image.new('RGB', (section_width, section_height), color=background_color)
    offset_x = S3LayoutRules.PAD_X.value
    offset_y = S3LayoutRules.PAD_Y.value
    
    content_padding = (section_height - S3LayoutRules.PAD_Y.value * 2 - total_content_height) // (len(img_dimens) - 1)
    for img, img_height in img_dimens:
        section3_img.paste(img, (offset_x, offset_y))
        offset_y += (img_height + content_padding)
    # Testing---------------------------------------------------
    # section3_img.show()
    # ----------------------------------------------------------
    return section3_img, section_height

# Testing-------------------------------------------------------
if __name__ == '__main__':
    img = render_rule_based_infographic(sample_data_without_visual_short)
    img.save(SAMPLE_IMAGE_PATH + "\\out_img1.png")

    img = render_rule_based_infographic(sample_data_without_visual_long)
    img.save(SAMPLE_IMAGE_PATH + "\\out_img2.png")

    img = render_rule_based_infographic(generate_sample_data_with_visual_short())
    img.save(SAMPLE_IMAGE_PATH + "\\out_img3.png")

    img = render_rule_based_infographic(generate_sample_data_with_visual_long())
    img.save(SAMPLE_IMAGE_PATH + "\\out_img4.png")
