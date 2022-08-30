/// <reference types="cypress" />

// H5P XBlock studio_view tests

describe('H5P Studio View', () => {

    it('displays h5p xblock in lms view', () => {

        // Save data on studio first
        cy.intercept('POST', '/handler/h5pplayerxblock.h5pxblock.d0.u0/studio_submit/*').as('studioSubmit')
        cy.studioSubmit()
        cy.wait('@studioSubmit')

        // Now access LMS
        cy.intercept('GET', '/h5pxblockmedia/h5pplayerxblock.h5pxblock.d0.u0/h5p.json').as('rootJson')        
        cy.visit(Cypress.env('LMS_URL'))
        cy.wait('@rootJson')
        
        // Make sure H5P content iframe is loaded and relevant buttons are visible
        cy.getIframe(".h5p-iframe").find('.h5p-drag-dropzone-container').should('have.length', 3)
        cy.getIframe(".h5p-iframe").find('a.h5p-link').should('be.visible')
        cy.getIframe(".h5p-iframe").find('.h5p-enable-fullscreen').should('be.visible')        
        cy.getIframe(".h5p-iframe").find('.h5p-question-check-answer').click({force: true})

    })

})
