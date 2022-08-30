Cypress.Commands.add('studioSubmit', () => {
    cy.visit(Cypress.env('STUDIO_URL'))
    cy.fixture('sampledata').then((data) => {
        cy.contains('Display Name')
        .parent()
        .find('input[id=xb_display_name]')
        .clear().type(data.xb_display_name)

        cy.contains('Reuse Existing H5P Content')
        .parent()
        .find('input[id=xb_existing_content_path]')
        .clear()

        cy.contains('Show H5P player frame')
        .parent()
        .find('select[id=xb_field_edit_show_frame]')
        .select(data.xb_field_edit_show_frame)

        cy.contains('Show copyright button')
        .parent()
        .find('select[id=xb_field_edit_show_copyright]')
        .select(data.xb_field_edit_show_copyright)

        cy.contains('Show h5p icon')
        .parent()
        .find('select[id=xb_field_edit_show_h5p]')
        .select(data.xb_field_edit_show_h5p)

        cy.contains('Show fullscreen button')
        .parent()
        .find('select[id=xb_field_edit_show_fullscreen]')
        .select(data.xb_field_edit_show_fullscreen)
        
        cy.contains('Is Scorable')
        .parent()
        .find('select[id=xb_field_edit_is_scorable]')
        .select(data.xb_field_edit_is_scorable)

        cy.contains('User content state save frequency')
        .parent()
        .find('input[id=xb_field_edit_save_freq]')
        .clear().type(data.xb_field_edit_save_freq)

        cy.get('input[id=xb_h5p_file]').selectFile('cypress/fixtures/' + data.h5p_file_upload)

    })
    cy.get('a.save-button').click()
})

Cypress.Commands.add('getIframe', (iframe) => {
    return cy.get(iframe).first()
        .its('0.contentDocument.body', {timeout: 10000})
        .should('not.be.empty')
        .then(cy.wrap);
})
