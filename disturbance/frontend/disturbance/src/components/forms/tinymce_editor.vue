<!-- 
  TinyMCE Editor Wrapper Component
  
  This component wraps TinyMCE to provide a rich text editor in Vue applications.
  It loads TinyMCE dynamically from django-tinymce static files to ensure version
  sync between backend (Django admin) and frontend (Vue). This eliminates npm duplication
  and maintains a single source of truth for the editor version.
-->
<template>
  <div class="tinymce-wrapper">
    <textarea ref="editor"></textarea>
  </div>
</template>

<script>
export default {
  name: 'tinymceEditor',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    height: {
      type: Number,
      default: 500
    }
  },
  emits: ['update:modelValue'],
  mounted() {
    /**
     * Initialize TinyMCE using the globally loaded instance from /static/tinymce/tinymce.min.js
     * The script is loaded once globally, not per-component, for better performance.
     */
    // Wait for TinyMCE to be available (in case of slow script loading)
    const initEditor = () => {
      if (!window.tinymce) {
        // Retry if TinyMCE not ready yet
        setTimeout(initEditor, 100);
        return;
      }

      window.tinymce.init({
        // Target the textarea ref to convert it into an editor
        target: this.$refs.editor,
        // Base path for TinyMCE assets (plugins, themes, skins)
        base_url: '/static/tinymce',
        // Use .min files (minified) for production
        suffix: '.min',
        license_key: 'gpl',
        // Show the menu bar (File, Edit, View, Insert, Format, etc.)
        menubar: true,
        // Fixed editor height (in pixels)
        height: this.height,
        min_height: this.height,
        max_height: this.height,
        // Disable manual resizing to maintain fixed height
        resize: false,
        // Hide TinyMCE promotion banner
        promotion: false,
        // Force vertical scrolling inside editor body for fixed-height editors
        content_style: 'body { overflow-y: scroll; font-family: Helvetica, Arial, sans-serif; padding: 8px; }',
        // List of enabled plugins for additional functionality
        plugins: 'advlist autolink lists link image charmap preview anchor searchreplace visualblocks insertdatetime media table wordcount codesample nonbreaking quickbars',
        // Toolbar layout mode: 'sliding' makes tools collapse into a menu on small screens
        toolbar_mode: 'sliding',
        // Toolbar buttons and groups (separated by |)
        toolbar: 'undo redo | blocks | fontfamily fontsize | bold italic underline strikethrough | forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image media table | blockquote charmap codesample nonbreaking | removeformat | preview',
        // Setup function: called during editor initialization
        setup: (editor) => {
          // Store the editor instance for use in other methods
          this.editor = editor;

          // When editor is fully initialized, populate it with the current modelValue
          editor.on('init', () => {
            editor.setContent(this.modelValue || '');
          });

          // Sync editor content back to Vue v-model whenever user makes changes
          editor.on('Change KeyUp Undo Redo SetContent', () => {
            this.$emit('update:modelValue', editor.getContent());
          });
        }
      });
    };

    // Initiate editor setup (checks if TinyMCE is already loaded)
    initEditor();
  },
  watch: {
    modelValue(newVal) {
      // Only update editor content if it has changed and editor instance exists
      if (this.editor && this.editor.getContent() !== (newVal || '')) {
        this.editor.setContent(newVal || '');
      }
    }
  },
  
  // Clean up TinyMCE instance before component is destroyed to prevent memory leaks
  beforeUnmount() {
    if (this.editor) {
      this.editor.remove();
      this.editor = null;
    }
  }
};
</script>

<style>
/* Wrapper container takes full width of parent */
.tinymce-wrapper {
  width: 100%;
}

/* 
  TinyMCE renders menus/dialogs in body-level containers with lower z-index
  than the custom modal in this app. These overrides ensure dropdowns/dialogs
  appear in front of the modal window (z-index: 20000). 
*/  
.tox-tinymce-aux,
.tox-menu,
.tox-collection,
.tox-dialog-wrap,
.tox .tox-dialog,
.tox .tox-menu,
.tox .tox-collection--list {
  z-index: 30001 !important;
}
</style>
