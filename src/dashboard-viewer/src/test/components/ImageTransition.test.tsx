import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ImageTransition } from '@/components/ImageTransition'

describe('ImageTransition', () => {
  const defaultProps = {
    currentImage: '/test-image-1.jpg',
    nextImage: null,
    isTransitioning: false,
    fadeDuration: 1000,
    className: 'test-class'
  }

  it('should render current image', () => {
    render(<ImageTransition {...defaultProps} />)

    const currentImg = screen.getByAltText('Dashboard')
    expect(currentImg).toBeInTheDocument()
    expect(currentImg).toHaveAttribute('src', '/test-image-1.jpg')
  })

  it('should render both images during transition', () => {
    render(
      <ImageTransition
        {...defaultProps}
        nextImage="/test-image-2.jpg"
        isTransitioning={true}
      />
    )

    const images = screen.getAllByAltText('Dashboard')
    expect(images).toHaveLength(2)

    // Current image should be fading out (opacity 0)
    expect(images[0]).toHaveStyle({ opacity: '0' })
    // Next image should be fading in (opacity 1)
    expect(images[1]).toHaveStyle({ opacity: '1' })
  })

  it('should only render current image when not transitioning', () => {
    render(
      <ImageTransition
        {...defaultProps}
        nextImage="/test-image-2.jpg"
        isTransitioning={false}
      />
    )

    const images = screen.getAllByAltText('Dashboard')
    expect(images).toHaveLength(2)

    // Current image should be visible (opacity 1)
    expect(images[0]).toHaveStyle({ opacity: '1' })
    // Next image should be hidden (opacity 0)
    expect(images[1]).toHaveStyle({ opacity: '0' })
  })

  it('should apply correct transition duration', () => {
    render(
      <ImageTransition
        {...defaultProps}
        fadeDuration={5000}
        isTransitioning={true}
        nextImage="/test-image-2.jpg"
      />
    )

    const images = screen.getAllByAltText('Dashboard')
    images.forEach(img => {
      expect(img).toHaveStyle({
        transition: 'opacity 5000ms ease-in-out'
      })
    })
  })

  it('should have black background by default', () => {
    const { container } = render(<ImageTransition {...defaultProps} />)

    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('bg-black')
  })

  it('should apply custom className', () => {
    const { container } = render(
      <ImageTransition {...defaultProps} className="custom-class" />
    )

    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('custom-class')
  })
})
