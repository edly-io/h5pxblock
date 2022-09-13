/// <reference types="cypress" />

// H5P XBlock studio_view tests

describe('H5P Studio View', () => {
    beforeEach(() => {
        cy.visit(Cypress.env('STUDIO_URL'))
    })

    it('displays h5p xblock in studio view and verify fist, last and file fields', () => {

        // h5p xblock should display file input field to display content.
        cy.get('.settings-list li #xb_h5p_file').should('have.length', 1)

        // First field should be Display name.
        cy.get('.settings-list li label').first().should('have.text', 'Display Name')
        cy.get('.settings-list li span').first().should('have.text', 'Display name for this module')

        // Last field should be Display name.
        cy.get('.settings-list li label').last().should('have.text', 'User content state save frequency')
        cy.get('.settings-list li span').last().should('to.contain', 'How often current user content state should be autosaved')

    })

    it('sets values in studio view fields and saves them', () => {
        // Fill all fields and submit
        cy.intercept('POST', '/handler/h5pplayerxblock.h5pxblock.d0.u0/studio_submit/*').as('studioSubmit')
        cy.studioSubmit()
        cy.wait('@studioSubmit')
        // Make sure progress bar updated after content is uploaded
        cy.get('.progress-bar-container').should('be.visible')
        cy.get('.progress-bar-container .progress-bar').should('have.text', 'Uploaded(100%)')

        cy.visit(Cypress.env('STUDIO_URL'))

        cy.fixture('sampledata').then((data) => {
            cy.contains('Display Name')
            .parent()
            .find('input[id=xb_display_name]')
            .should('have.value', data.xb_display_name)
            
            cy.contains('Currently:')
            .parent()
            .should('to.contain', data.h5p_file_upload)
            cy.contains('Reuse Existing H5P Content')
            .parent()
            .find('input[id=xb_existing_content_path]')
            .should('have.value', '/h5pxblockmedia/h5pplayerxblock.h5pxblock.d0.u0')

            cy.contains('Show H5P player frame')
            .parent()
            .find('select[id=xb_field_edit_show_frame]')
            .should('have.value', data.xb_field_edit_show_frame)

            cy.contains('Show copyright button')
            .parent()
            .find('select[id=xb_field_edit_show_copyright]')
            .should('have.value', data.xb_field_edit_show_copyright)

            cy.contains('Show h5p icon')
            .parent()
            .find('select[id=xb_field_edit_show_h5p]')
            .should('have.value', data.xb_field_edit_show_h5p)

            cy.contains('Show fullscreen button')
            .parent()
            .find('select[id=xb_field_edit_show_fullscreen]')
            .should('have.value', data.xb_field_edit_show_fullscreen)
            
            cy.contains('Is Scorable')
            .parent()
            .find('select[id=xb_field_edit_is_scorable]')
            .should('have.value', data.xb_field_edit_is_scorable)

            cy.contains('User content state save frequency')
            .parent()
            .find('input[id=xb_field_edit_save_freq]')
            .should('have.value', data.xb_field_edit_save_freq)

        })

    })

})
