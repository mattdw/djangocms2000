var djangocms2000 = function ($, highlight_start_color, highlight_end_color, tinymce_init_object) {
	
	var throbberString = "<span class='throbber'>Saving...</span>",
		currently_editing = false;
	
	if (!tinymce_init_object) {
	    tinymce_init_object = {
			/*
			setup: function(ed) {
       
				// Force Paste-as-Plain-Text
				ed.onPaste.add( function(ed, e, o) {
					ed.execCommand('mcePasteText', true);
					return tinymce.dom.Event.cancel(e);
				});
			   
			},
			*/
			"elements": "id_raw_content",
			"language": "en",
			"directionality": "ltr",
			"theme": "advanced",
			"strict_loading_mode": 1,
			"mode": "exact",
			"height": "400px",
			"width": "760px",
			"content_css" : "/djangocms2000/media/css/tinymce_content.css",
			"theme_advanced_toolbar_location" : "top",
			"theme_advanced_toolbar_align" : "left",
			"theme_advanced_buttons1" : "h1,h2,h3,h4,|,bold,italic,|,undo,redo,|,link,|,bullist,numlist,|,pastetext,code",
			"theme_advanced_buttons2" : "",
			"theme_advanced_buttons3" : "",
			"plugins" : "heading,paste",
			"relative_urls" : false
		}
	}
	
	
	
	
	/*
	$('body').css({
		'padding-top': '30px'
	});
	*/
	
	//$("#djangocms2000-menu").prependTo('body');
	//var topMenu = $("#djangocms2000-menu").clone();
	//$('body').remove("#djangocms2000-menu");
	//$('body').prepend(topMenu);
	
	function edit(block) {
		//console.log(block, currently_editing, $(block).attr('type'));
		
		if (currently_editing) {
			return false;
		}
		
		
		if ($(block).hasClass('placeholder')) {
			var raw_content = '';
		}
		else {
			var raw_content = $.trim($(block).find('input').val());
		}
		
		if ($(block).attr('blocktype') === 'image') {
			$('#djangocms2000-imageform #id_image_id').val($(block).attr('image_id'));
			$('#djangocms2000-imageform #id_redirect_to').val(window.location);
			
			if ($(block).find('img').length) {
				$('#djangocms2000-imageform h2').html('Change image');
				$('#djangocms2000-imageform div.current img').attr('src', $(block).find('img').eq(0).attr('src'));
				$('#djangocms2000-imageform div.current').css({'display': 'block'});
			}
			else {
				$('#djangocms2000-imageform h2').html('Add image');
				$('#djangocms2000-imageform div.current').css({'display': 'none'});
			}
			
			$('#djangocms2000-imageoverlay').css({opacity: 0, display: 'block'}).animate({opacity: 1}, 300);
		}
		else if ($(block).attr('format') === 'html') {
			$('#djangocms2000-htmlform #id_raw_content').val(raw_content).html(raw_content);
			tinyMCE.get("id_raw_content").setContent(raw_content);
			$('#djangocms2000-htmlform #id_block_id').val($(block).attr('block_id'));
			$('#djangocms2000-htmlform #id_format').val($(block).attr('format'));

			$('#djangocms2000-htmlform form').ajaxForm({
				'success': function(data) {
					var raw_content = $.trim(data.raw_content),
						compiled_content = $.trim(data.compiled_content);
					$(block).find('input').val(raw_content);
					$(block).find("span.inner").html(compiled_content || "Click to add " + $(block).attr('label'));
					
					if (!compiled_content) {
						$(block).addClass("placeholder");
					}
					highlightBlock(block);
					currently_editing = false;
					
				},
				'beforeSubmit': function() {
					$(block).removeClass("placeholder");
					$(block).find("span.inner").html(throbberString);
					hideForm('html', false);
				},
				'dataType': 'json'
			});
			$('#djangocms2000-htmloverlay').css({opacity: 0, display: 'block'}).animate({opacity: 1}, 300);
		}
		else {
			$('#djangocms2000-textform #id_raw_content').val(raw_content).html(raw_content);
			$('#djangocms2000-textform #id_block_id').val($(block).attr('block_id'));
			$('#djangocms2000-textform #id_format').val($(block).attr('format'));
			
			var editFormContainer = $('#djangocms2000-textform').clone();
			editFormContainer.find('textarea').css({'height': $(block).height()});
			editFormContainer.css({'display': 'block'});
			
			$(block).parent().append(editFormContainer);
			$(block).css({'display': 'none'});
			
			
			
			editFormContainer.find('textarea').focus().select();
			
			function hideTextForm() {
				$(block).css({'display': 'block'});
				editFormContainer.remove();
				currently_editing = false;
			};
			editFormContainer.find('input.cancel').click(hideTextForm);
			

			editFormContainer.find('form').ajaxForm({
				'success': function(data) {
					var raw_content = $.trim($('<div>').text(data.raw_content).html());
					$(block).find("span.inner").html(raw_content || "Click to add " + $(block).attr('label'));
					if (!raw_content) {
						$(block).addClass("placeholder");
					}
					highlightBlock(block);
					currently_editing = false;
					$(block).find('input').val(raw_content);
				},
				'beforeSubmit': function() {
					$(block).removeClass("placeholder");
					$(block).find("span.inner").html(throbberString);
					hideTextForm();
				},
				'dataType': 'json'
			});			
		}

		
		
		currently_editing = true;
	};
	
	
	$(function() {
	
		tinyMCE.init(tinymce_init_object);

		$('#djangocms2000-htmlform input.cancel').click(function() {
			hideForm('html');
		});	
		$('#djangocms2000-imageform input.cancel').click(function() {
			hideForm('image');
		});		
		
		$('.djangocms2000-block, .djangocms2000-image').each(function() {
			$(this).append('<span class="editMarker"></span>');
		}).mouseover(function() {
			if (!currently_editing) {
				$(this).addClass('hovered').find('span.editMarker').css({'display': 'block'});
			}
		}).mouseout(function() {
			$(this).removeClass('hovered').find('span.editMarker').css({'display': 'none'});
		}).click(function(){
			edit(this);
			return false;
		}).find('span.editMarker').click(function(){
			edit(this.parentNode);
			return false;
		});
		
		
	});
	
	function highlightBlock(block) {
		//var bg = $(block).css('backgroundColor');
		//console.log(highlight_start_color, highlight_end_color);
		
		$(block).css({backgroundColor: (highlight_start_color || "#ff0")}).animate({backgroundColor: (highlight_end_color || "#fff")}, 500, function() {
			$(block).css({backgroundColor: ("")});	
		});
	};

	
	function hideForm(which, animate) {
		var overlay = $('#djangocms2000-' + which + 'overlay');
		if (animate === false) {
			overlay.css({display: 'none'});
		}
		else {
			overlay.animate({opacity: 0}, 'fast', function() {
				overlay.css({display: 'none'});
			});
		}
		currently_editing = false;

	};



}; //init done inline so settings can be passed in - see templates/editor.html

